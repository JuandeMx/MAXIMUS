#!/usr/bin/env python3
import http.server
import socketserver
import urllib.parse
import urllib.request
import os
import time
import tarfile
import threading
import re

PORT = 6767
KEYS_FILE = "/etc/MaximusVpsMx/keys.db"
PANEL_DIR = "/etc/MaximusVpsMx"
TAR_FILE = "/tmp/panel_master.tar.gz"

def create_tarball():
    with tarfile.open(TAR_FILE, "w:gz") as tar:
        for item in os.listdir(PANEL_DIR):
            # Exclude sensitive local databases and config files
            if item in ["keys.db", "users.db", "hysteria_users.db", "bot_config.json", ".master_node", "cloudflare.conf", ".git", ".gitignore", "chat_export", "MaximusWA", "license.key"]:
                continue
            item_path = os.path.join(PANEL_DIR, item)
            tar.add(item_path, arcname=item)
    return TAR_FILE

def read_keys():
    if not os.path.exists(KEYS_FILE):
        open(KEYS_FILE, 'a').close()
    keys = {}
    with open(KEYS_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split(':')
            if len(parts) >= 5:
                # Format: KEY:STATUS:ACTIVATION_EPOCH:IP:CREATED_EPOCH[:TYPE]
                keys[parts[0]] = {
                    'status': parts[1],
                    'activation_epoch': int(parts[2]),
                    'ip': parts[3],
                    'created_epoch': int(parts[4]),
                    'type': parts[5] if len(parts) >= 6 else '30D'
                }
    return keys

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        for k, v in keys.items():
            f.write(f"{k}:{v['status']}:{v['activation_epoch']}:{v['ip']}:{v['created_epoch']}:{v.get('type', '30D')}\n")

class KeyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)
        client_ip = self.client_address[0]
        
        # Omitir favicon
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # Validación común de la key
        if path in ["/install", "/download", "/check", "/activate"]:
            key = query.get('key', [''])[0]
            if not key:
                self.send_error(400, "Missing Key")
                return
                
            keys = read_keys()
            if key not in keys:
                self.send_error(403, "Invalid Key")
                return
                
            kdata = keys[key]
            current_time = int(time.time())
            
            # Verificar expiración si está usada
            if kdata['status'] == 'USED':
                if current_time > kdata['activation_epoch'] and kdata['activation_epoch'] != 0:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"EXPIRED")
                    return
                # Verificar IP (Anti-piratería)
                if kdata['ip'] != 'NONE' and kdata['ip'] != client_ip:
                    self.send_error(403, "Key is locked to another IP")
                    return

            # Manejo de Rutas
            if path == "/install":
                # Devolver el instalador modificado con la IP del maestro
                install_path = os.path.join(PANEL_DIR, "install.sh")
                if not os.path.exists(install_path):
                    self.send_error(404, "Installer not found")
                    return
                
                with open(install_path, 'r') as f:
                    content = f.read()
                
                # Inyectamos variables
                master_ip = self.headers.get('Host', '').split(':')[0]
                if not master_ip:
                    master_ip = "127.0.0.1"
                
                injection = f"\nMASTER_IP='{master_ip}'\nMASTER_PORT='{PORT}'\nCLIENT_KEY='{key}'\n"
                content = content.replace("#!/bin/bash", "#!/bin/bash" + injection)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                
            elif path == "/download":
                create_tarball()
                self.send_response(200)
                self.send_header('Content-type', 'application/gzip')
                self.end_headers()
                with open(TAR_FILE, 'rb') as f:
                    self.wfile.write(f.read())
                    
            elif path == "/activate":
                if kdata['status'] == 'UNUSED':
                    kdata['status'] = 'USED'
                    kdata['ip'] = client_ip
                    if kdata.get('type') == 'ILIMITED':
                        kdata['activation_epoch'] = 0
                    else:
                        # 30 días = 2592000
                        kdata['activation_epoch'] = current_time + 2592000
                    save_keys(keys)
                    
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"ACTIVATED")
                
            elif path == "/check":
                ktype = kdata.get('type', '30D')
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"OK:{ktype}".encode('utf-8'))
            return
            
        elif path == "/setup":
            # Devolver el instalador modificando SOLO MASTER_IP y MASTER_PORT (la Key viene por argumento)
            install_path = os.path.join(PANEL_DIR, "install.sh")
            if not os.path.exists(install_path):
                self.send_error(404, "Installer not found")
                return
            try:
                with open(install_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # El dominio puede ser el de CF o la IP
                domain_file = os.path.join(PANEL_DIR, "domain.conf")
                cf_domain_file = os.path.join(PANEL_DIR, "cloudflare.conf")
                
                if os.path.exists(domain_file):
                    with open(domain_file, "r") as f:
                        host_url = f.read().strip()
                elif os.path.exists(cf_domain_file):
                    with open(cf_domain_file, "r") as f:
                        host_url = f.read().strip()
                else:
                    try:
                        public_ip = urllib.request.urlopen('https://ifconfig.me').read().decode('utf8').strip()
                    except:
                        public_ip = "127.0.0.1"
                    host_url = f"http://{public_ip}:6767"

                # Inyectar MASTER_URL para evitar problemas con puertos https implícitos (443)
                master_ip_raw = host_url.replace("https://", "").replace("http://", "").split(":")[0]
                injection = f"\nMASTER_URL='{host_url}'\nMASTER_IP='{master_ip_raw}'\nMASTER_PORT='80'\n"
                content = content.replace("#!/bin/bash", "#!/bin/bash" + injection)
                
                self.send_response(200)
                self.send_header("Content-type", "text/x-shellscript")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))

def run_server():
    server_address = ('0.0.0.0', PORT)
    httpd = socketserver.TCPServer(server_address, KeyHandler)
    print(f"Master Key Server running on port {PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
