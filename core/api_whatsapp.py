#!/usr/bin/env python3
import json
import subprocess
import datetime
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API_SECRET = "MaximusSecret2026!"
USER_DB = "/etc/MaximusVpsMx/users.db"

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/add_hwid':
            auth_header = self.headers.get('Authorization')
            if auth_header != f"Bearer {API_SECRET}":
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Unauthorized"}')
                return

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
            except:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Invalid JSON"}')
                return

            hwid = data.get('hwid', '').lower()
            alias = data.get('alias', 'WhatsappUser').replace(' ', '_').replace(':', '')
            days = data.get('days', 4)
            is_extend = data.get('extend', False)

            if not hwid or not hwid.isalnum():
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Invalid HWID"}')
                return

            current_exp = None
            if is_extend and os.path.exists(USER_DB):
                with open(USER_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split(':')
                        if len(parts) >= 6 and parts[0] == hwid:
                            current_exp = parts[2]
                            alias = parts[5] # Keep original alias
                            break
            
            if current_exp:
                try:
                    base_date = datetime.datetime.strptime(current_exp, "%Y-%m-%d")
                    if base_date < datetime.datetime.now():
                        base_date = datetime.datetime.now()
                except:
                    base_date = datetime.datetime.now()
            else:
                base_date = datetime.datetime.now()

            exp_date = (base_date + datetime.timedelta(days=days)).strftime("%Y-%m-%d")

            # Execute bash commands to create linux user securely
            subprocess.run(["useradd", "-M", "-s", "/bin/false", hwid], stderr=subprocess.DEVNULL)
            
            p = subprocess.Popen(["chpasswd"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            p.communicate(input=f"{hwid}:{hwid}".encode())

            # Remove existing if any from users.db
            if os.path.exists(USER_DB):
                subprocess.run(["sed", "-i", f"/^{hwid}:/d", USER_DB])
            
            # Append to users.db (New Format)
            with open(USER_DB, "a") as f:
                f.write(f"{hwid}:HWID_INV:{exp_date}:{hwid}:1:{alias}\n")

            print(f"[API] HWID Registrado con exito: {hwid} | {alias} | {days} dias")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "hwid": hwid, "exp": exp_date}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Desactivar logs innecesarios para mantener la consola limpia
        pass

if __name__ == '__main__':
    port = 8085
    server = ThreadingHTTPServer(('0.0.0.0', port), RequestHandler)
    print(f"🚀 Maximus API Iniciada en el puerto {port} (Multi-hilo)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
