#!/usr/bin/env python3
"""
MaximusVpsMx - Master Web Panel Backend Server & Real SSH Multi-Node Provisioner
Port: 8080
Serves Web Panel UI + Handles REAL Linux user creation + REAL SSH VPS provisioning
"""

import os
import sys
import json
import time
import subprocess
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

PORT = 8080
CONFIG_DIR = "/etc/MaximusVpsMx"
WEB_DIR = os.path.join(CONFIG_DIR, "web-panel")
USERS_DB = os.path.join(CONFIG_DIR, "users.db")
NODES_DB = os.path.join(CONFIG_DIR, "nodes_servers.db")
METHODS_DB = os.path.join(CONFIG_DIR, "connection_methods.db")

os.makedirs(CONFIG_DIR, exist_ok=True)
touch_files = [USERS_DB, NODES_DB, METHODS_DB]
for tf in touch_files:
    if not os.path.exists(tf):
        with open(tf, "w") as f:
            pass

def execute_local_user_create(username, password, days):
    """Crea el usuario REAL en el sistema Linux local de la VPS"""
    try:
        days = int(days)
    except ValueError:
        days = 30

    exp_date = (datetime.date.today() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")

    # 1. useradd en Linux OS
    subprocess.run(["userdel", "-f", username], stderr=subprocess.DEVNULL)
    cmd_create = ["useradd", "-M", "-s", "/bin/false", "-e", exp_date, username]
    subprocess.run(cmd_create, stderr=subprocess.DEVNULL)

    # 2. chpasswd
    chpass = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    chpass.communicate(input=f"{username}:{password}".encode("utf-8"))

    # 3. Guardar en users.db local de Maximus
    lines = []
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            lines = f.readlines()
    
    with open(USERS_DB, "w") as f:
        for l in lines:
            if not l.startswith(f"{username}:"):
                f.write(l)
        f.write(f"{username}:{password}:{exp_date}\n")

    return True, exp_date

def execute_local_user_delete(username):
    """Elimina el usuario REAL del sistema Linux OS"""
    subprocess.run(["userdel", "-f", username], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-u", username], stderr=subprocess.DEVNULL)
    
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            lines = f.readlines()
        with open(USERS_DB, "w") as f:
            for l in lines:
                if not l.startswith(f"{username}:"):
                    f.write(l)
    return True

class MasterWebHandler(BaseHTTPRequestHandler):

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # ----------------------------------------------------------------------
        # API ENDPOINTS
        # ----------------------------------------------------------------------
        if parsed.path == "/api/clients":
            users = []
            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) >= 3:
                            pass_str = parts[1]
                            exp_str = parts[2]
                            users.append({
                                "id": hash(parts[0]),
                                "username": parts[0],
                                "password": pass_str,
                                "exp_date": exp_str,
                                "days": 30,
                                "devices": 1,
                                "status": "Active"
                            })
            self._send_json(200, {"clients": users})
            return

        if parsed.path == "/api/nodes":
            nodes = []
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 3:
                            nodes.append({
                                "id": hash(parts[1]),
                                "name": parts[0],
                                "ip": parts[1],
                                "port": int(parts[2]),
                                "status": "ONLINE",
                                "users": 1
                            })
            # Si no hay nodos, agregar el nodo local por defecto
            if not nodes:
                nodes.append({
                    "id": 1,
                    "name": "Servidor Local (Master)",
                    "ip": "127.0.0.1",
                    "port": 22,
                    "status": "ONLINE",
                    "users": 1
                })
            self._send_json(200, {"nodes": nodes})
            return

        if parsed.path == "/api/methods":
            methods = []
            if os.path.exists(METHODS_DB):
                with open(METHODS_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 5:
                            methods.append({
                                "id": hash(parts[0]),
                                "name": parts[0],
                                "protocol": parts[1],
                                "sni": parts[2],
                                "payload": parts[3],
                                "port": int(parts[4])
                            })
            self._send_json(200, {"methods": methods})
            return

        # ----------------------------------------------------------------------
        # ARCHIVOS ESTÁTICOS DE LA WEB (index.html, style.css, app.js)
        # ----------------------------------------------------------------------
        file_path = parsed.path.lstrip("/")
        if not file_path:
            file_path = "index.html"

        full_file_path = os.path.join(WEB_DIR, file_path)
        if os.path.exists(full_file_path) and os.path.isfile(full_file_path):
            content_type = "text/html"
            if file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".png"):
                content_type = "image/png"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(full_file_path, "rb") as f:
                self.wfile.write(f.read())
            return

        self._send_json(404, {"error": "File or endpoint not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            payload = {}

        # ----------------------------------------------------------------------
        # POST /api/client/create (CREACIÓN REAL EN LINUX)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/client/create":
            username = payload.get("username", "").strip().upper()
            password = payload.get("password", "").strip()
            days = payload.get("days", 30)

            if not username or not password:
                self._send_json(400, {"error": "Username and password required"})
                return

            # 1. Crear localmente en este servidor VPS Master
            success, exp_date = execute_local_user_create(username, password, days)

            # 2. Replicar a otros nodos VPS guardados en nodes_servers.db
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 3 and parts[1] != "127.0.0.1":
                            nip = parts[1]
                            # Intentar enviar la orden por API al nodo remoto
                            try:
                                import urllib.request
                                req_data = json.dumps({"username": username, "password": password, "days": days}).encode("utf-8")
                                req = urllib.request.Request(f"http://{nip}:6767/api/v1/client/create", data=req_data, headers={
                                    "Content-Type": "application/json",
                                    "X-API-KEY": "maximus_secret_node_key_2026"
                                })
                                urllib.request.urlopen(req, timeout=3)
                            except Exception as e:
                                print(f"Error sync to remote node {nip}: {e}")

            self._send_json(200, {
                "success": True,
                "message": f"Usuario REAL '{username}' creado exitosamente en Linux OS.",
                "username": username,
                "password": password,
                "exp_date": exp_date
            })
            return

        # ----------------------------------------------------------------------
        # POST /api/client/delete
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/client/delete":
            username = payload.get("username", "").strip()
            if username:
                execute_local_user_delete(username)
            self._send_json(200, {"success": True, "message": f"Usuario '{username}' eliminado."})
            return

        # ----------------------------------------------------------------------
        # POST /api/vps/install (INSTALACIÓN REAL SSH REMOTA O LOCAL)
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/vps/install":
            name = payload.get("name", "VPS Remote")
            ip = payload.get("ip", "").strip()
            port = payload.get("port", 22)
            user = payload.get("user", "root")
            password = payload.get("password", "")

            # Guardar nodo en nodes_servers.db
            with open(NODES_DB, "a") as f:
                f.write(f"{name}|{ip}|{port}\n")

            # Ejecutar comando de instalación real si es por SSH
            install_cmd = "apt-get update -y && apt-get install -y git && rm -rf /tmp/MaximusVpsMx && git clone https://github.com/JuandeMx/MAXIMUS.git /tmp/MaximusVpsMx && cd /tmp/MaximusVpsMx && chmod +x install.sh && bash install.sh && mkdir -p /etc/MaximusVpsMx && touch /etc/MaximusVpsMx/.master_node"
            
            if ip in ["127.0.0.1", "localhost"] or ip == os.popen("curl -s4 ifconfig.me").read().strip():
                # Instalación local
                subprocess.Popen(install_cmd, shell=True)
            else:
                # Instalación remota SSH usando sshpass si está disponible
                ssh_cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -p {port} {user}@{ip} '{install_cmd}'"
                subprocess.Popen(ssh_cmd, shell=True)

            self._send_json(200, {
                "success": True,
                "message": f"Instalación REAL iniciada en SSH para {ip}.",
                "ip": ip
            })
            return

        # ----------------------------------------------------------------------
        # POST /api/method/create
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/method/create":
            name = payload.get("name", "")
            protocol = payload.get("protocol", "")
            sni = payload.get("sni", "")
            payload_str = payload.get("payload", "")
            port = payload.get("port", 443)

            with open(METHODS_DB, "a") as f:
                f.write(f"{name}|{protocol}|{sni}|{payload_str}|{port}\n")

            self._send_json(200, {"success": True, "message": f"Método '{name}' guardado."})
            return

        self._send_json(404, {"error": "Endpoint not found"})

def run():
    print(f"🚀 Maximus Master Web Backend Server running on http://0.0.0.0:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), MasterWebHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Master Web server...")
        server.server_close()

if __name__ == "__main__":
    run()
