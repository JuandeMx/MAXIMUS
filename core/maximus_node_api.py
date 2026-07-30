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
            # Status check
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
            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) >= 2:
                            users.append({"username": parts[0], "exp_date": parts[1] if len(parts) > 1 else ""})
            self._send_json(200, {"users": users})
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
