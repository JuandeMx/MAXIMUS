#!/usr/bin/env python3
"""
MaximusVpsMx - Multi-Node Sync API Server (Port 6767)
Handles remote multi-VPS user creation, renewal, deletion, and connection method sync.
Runs using standard Python 3 http.server (Zero external dependencies).
"""

import os
import sys
import json
import subprocess
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

PORT = 6767
CONFIG_DIR = "/etc/MaximusVpsMx"
TOKEN_FILE = os.path.join(CONFIG_DIR, "api_token.conf")
USERS_DB = os.path.join(CONFIG_DIR, "users.db")
V2RAY_CONF = os.path.join(CONFIG_DIR, "v2ray", "config.json")
V2RAY_CLIENTS_DB = os.path.join(CONFIG_DIR, "v2ray_clients.db")

def get_api_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    # Token por defecto si no existe
    default_token = "maximus_secret_node_key_2026"
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(default_token)
    return default_token

def get_online_counts():
    online_map = {}
    try:
        # 1. Conexiones SSHD
        cmd_ssh = "ps -u -p $(pgrep sshd) 2>/dev/null | tail -n +2 | awk '{print $1}'"
        res_ssh = subprocess.run(cmd_ssh, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_ssh.stdout:
            for u in res_ssh.stdout.splitlines():
                u = u.strip()
                if u and u != "root":
                    online_map[u] = online_map.get(u, 0) + 1
        
        # 2. Conexiones Dropbear / Netstat
        cmd_db = "netstat -tnp 2>/dev/null | grep -E 'sshd|dropbear' | grep ESTABLISHED | awk '{print $7}' | cut -d/ -f1"
        res_db = subprocess.run(cmd_db, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_db.stdout:
            for pid in res_db.stdout.splitlines():
                pid = pid.strip()
                if pid.isdigit():
                    res_owner = subprocess.run(["ps", "-o", "user=", "-p", pid], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    u_owner = res_owner.stdout.strip()
                    if u_owner and u_owner != "root":
                        online_map[u_owner] = online_map.get(u_owner, 0) + 1
    except Exception:
        pass
    return online_map

class NodeAPIHandler(BaseHTTPRequestHandler):

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-KEY")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-KEY")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.end_headers()

    def _authenticate(self):
        auth_header = self.headers.get("X-API-KEY") or self.headers.get("Authorization")
        if not auth_header:
            return False
        token = auth_header.replace("Bearer ", "").strip()
        return token == get_api_token()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ["/api/v1/health", "/status", "/"]:
            users_count = 0
            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    users_count = len([line for line in f if line.strip()])
            
            self._send_json(200, {
                "status": "ONLINE",
                "version": "7.3",
                "hostname": os.uname().nodename,
                "users_registered": users_count,
                "timestamp": datetime.datetime.now().isoformat()
            })
            return

        if not self._authenticate():
            self._send_json(401, {"error": "Unauthorized. Invalid X-API-KEY."})
            return

        if parsed.path == "/api/v1/users":
            users = []
            online_map = get_online_counts()
            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) >= 2:
                            u_name = parts[0]
                            exp_d = parts[1]
                            dev_limit = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
                            users.append({
                                "username": u_name,
                                "exp_date": exp_d,
                                "devices": dev_limit,
                                "online_count": online_map.get(u_name, 0)
                            })
            self._send_json(200, {"users": users})
            return

        if parsed.path == "/api/v1/protocols/status":
            services = {
                "ssh": "ssh",
                "dropbear": "dropbear",
                "stunnel": "stunnel4",
                "hysteria": "hysteria",
                "v2ray": "maximus-v2ray",
                "badvpn": "badvpn",
                "slowdns": "mx-slowdns"
            }
            statuses = {}
            for key, svc in services.items():
                res = subprocess.run(["systemctl", "is-active", "--quiet", svc])
                statuses[key] = "ONLINE" if res.returncode == 0 else "STOPPED"

            self._send_json(200, {"protocols": statuses})
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        if not self._authenticate():
            self._send_json(401, {"error": "Unauthorized. Invalid X-API-KEY."})
            return

        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            payload = {}

        # ----------------------------------------------------------------------
        # ENDPOINT 1: CREAR CLIENTE REMOTO (SSH / DROPBEAR / V2RAY)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/v1/client/create":
            username = payload.get("username")
            password = payload.get("password")
            days = payload.get("days", 30)

            if not username or not password:
                self._send_json(400, {"error": "Username and password are required."})
                return

            try:
                days = int(days)
            except ValueError:
                days = 30

            exp_date = (datetime.date.today() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")

            # 1. Crear usuario en el Sistema Linux (SSH / Dropbear)
            subprocess.run(["userdel", "-f", username], stderr=subprocess.DEVNULL)
            cmd_create = ["useradd", "-M", "-s", "/bin/false", "-e", exp_date, username]
            res = subprocess.run(cmd_create, capture_output=True, text=True)

            # Establecer contraseña
            chpass = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            chpass.communicate(input=f"{username}:{password}".encode("utf-8"))

            # 2. Registrar en DB local
            os.makedirs(CONFIG_DIR, exist_ok=True)
            # Limpiar usuario previo en users.db
            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    lines = f.readlines()
                with open(USERS_DB, "w") as f:
                    for l in lines:
                        if not l.startswith(f"{username}:"):
                            f.write(l)
            with open(USERS_DB, "a") as f:
                f.write(f"{username}:{password}:{exp_date}\n")

            self._send_json(200, {
                "success": True,
                "message": f"User '{username}' created successfully on node.",
                "username": username,
                "exp_date": exp_date,
                "days": days
            })
            return

        # ----------------------------------------------------------------------
        # ENDPOINT 2: RENOVAR CLIENTE (AGREGAR DÍAS)
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/v1/client/renew":
            username = payload.get("username")
            add_days = payload.get("days", 30)

            if not username:
                self._send_json(400, {"error": "Username is required."})
                return

            try:
                add_days = int(add_days)
            except ValueError:
                add_days = 30

            # Obtener fecha actual o exp
            new_exp = (datetime.date.today() + datetime.timedelta(days=add_days)).strftime("%Y-%m-%d")
            subprocess.run(["usermod", "-e", new_exp, username], stderr=subprocess.DEVNULL)

            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    lines = f.readlines()
                with open(USERS_DB, "w") as f:
                    for l in lines:
                        if l.startswith(f"{username}:"):
                            parts = l.strip().split(":")
                            pass_str = parts[2] if len(parts) > 2 else ""
                            f.write(f"{username}:{new_exp}:{pass_str}\n")
                        else:
                            f.write(l)

            self._send_json(200, {
                "success": True,
                "message": f"User '{username}' renewed until {new_exp}.",
                "new_exp_date": new_exp
            })
            return

        # ----------------------------------------------------------------------
        # ENDPOINT 3: ELIMINAR CLIENTE
        # ----------------------------------------------------------------------
        elif parsed.path in ["/api/v1/client/delete", "/api/v1/client/remove"]:
            username = payload.get("username")
            if not username:
                self._send_json(400, {"error": "Username is required."})
                return

            subprocess.run(["userdel", "-f", username], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-u", username], stderr=subprocess.DEVNULL)

            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    lines = f.readlines()
                with open(USERS_DB, "w") as f:
                    for l in lines:
                        if not l.startswith(f"{username}:"):
                            f.write(l)

            self._send_json(200, {
                "success": True,
                "message": f"User '{username}' deleted successfully from node."
            })
            return

        # ----------------------------------------------------------------------
        # ENDPOINT 4: CONTROL REMOTO DE PROTOCOLOS Y SERVICIOS
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/v1/protocols/control":
            svc_key = payload.get("service")
            action = payload.get("action", "restart")

            services = {
                "ssh": "ssh",
                "dropbear": "dropbear",
                "stunnel": "stunnel4",
                "hysteria": "hysteria",
                "v2ray": "maximus-v2ray",
                "badvpn": "badvpn",
                "slowdns": "mx-slowdns"
            }

            svc_name = services.get(svc_key)
            if not svc_name:
                self._send_json(400, {"error": "Servicio de protocolo no válido."})
                return

            if action in ["start", "stop", "restart"]:
                subprocess.run(["systemctl", action, svc_name], stderr=subprocess.DEVNULL)
                self._send_json(200, {"success": True, "message": f"Protocolo '{svc_key}' {action}ed."})
                return

            self._send_json(400, {"error": "Acción no soportada."})
            return

        self._send_json(404, {"error": "Endpoint not found"})

def run_server():
    token = get_api_token()
    print(f"🚀 Maximus Multi-Node API Server running on port {PORT}")
    print(f"🔑 API Secret Token: {token}")
    server = HTTPServer(("0.0.0.0", PORT), NodeAPIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API server...")
        server.server_close()

if __name__ == "__main__":
    run_server()
