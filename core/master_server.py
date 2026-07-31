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

# Importar generador de perfiles cifrados .MX
generate_mx_file = None

def load_mx_generator():
    global generate_mx_file
    if generate_mx_file is not None:
        return True
    try:
        core_dir = os.path.dirname(os.path.abspath(__file__))
        if core_dir not in sys.path:
            sys.path.insert(0, core_dir)
        import importlib
        mx_mod = importlib.import_module("mx_generator")
        generate_mx_file = mx_mod.generate_mx_file
        print("[MX Generator] ✅ Módulo mx_generator cargado correctamente.")
        return True
    except Exception as e1:
        print(f"[MX Generator] ⚠️ Primera carga falló: {e1}")
        print("[MX Generator] Intentando instalar pycryptodome...")
        try:
            subprocess.run(["pip3", "install", "pycryptodome", "--break-system-packages"],
                           capture_output=True, timeout=30)
        except Exception:
            try:
                subprocess.run(["pip3", "install", "pycryptodome"],
                               capture_output=True, timeout=30)
            except Exception:
                pass
        try:
            import importlib
            mx_mod = importlib.import_module("mx_generator")
            generate_mx_file = mx_mod.generate_mx_file
            print("[MX Generator] ✅ Módulo mx_generator cargado tras instalar pycryptodome.")
            return True
        except Exception as e2:
            print(f"[MX Generator] ❌ No se pudo cargar mx_generator: {e2}")
            print("[MX Generator] El servidor funcionará SIN generación de archivos .MX")
            generate_mx_file = None
            return False

load_mx_generator()

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

# Diccionario global para rastrear instalaciones en curso
_install_jobs = {}

def _safe_hash(s):
    """Genera un hash entero de 31 bits positivo determinista para compatibilidad con JS"""
    h = 5381
    for char in s:
        h = ((h << 5) + h) + ord(char)
    return h & 0x7FFFFFFF

def _ssh_run(ip, port, user, password, cmd):
    """Ejecuta un comando remoto por SSH usando sshpass. Retorna (exit_code, output)"""
    ssh_cmd = f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p {port} {user}@{ip} '{cmd}'"
    result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=300)
    return result.returncode, result.stdout + result.stderr

def _run_real_ssh_install(install_id, ip, port, user, password):
    """Hilo de fondo que ejecuta la instalación REAL paso a paso por SSH"""
    job = _install_jobs[install_id]

    # Paso 0: Asegurar que sshpass esté instalado localmente en el Master
    job["step"] = 0
    job["status"] = "Instalando sshpass en el Master..."
    job["log"].append("[+] Verificando sshpass en el servidor Master...")
    subprocess.run("apt-get install -y sshpass >/dev/null 2>&1", shell=True)
    job["log"].append("[OK] sshpass listo.")

    steps = [
        {
            "msg": "Probando conexión SSH...",
            "cmd": "echo 'SSH_OK'",
            "check": "SSH_OK"
        },
        {
            "msg": "Actualizando paquetes base (apt-get update)...",
            "cmd": "apt-get update -y >/dev/null 2>&1 && apt-get install -y git >/dev/null 2>&1 && echo 'APT_OK'",
            "check": "APT_OK"
        },
        {
            "msg": "Clonando repositorio MaximusVpsMx...",
            "cmd": "rm -rf /tmp/MaximusVpsMx && git clone https://github.com/JuandeMx/MAXIMUS.git /tmp/MaximusVpsMx >/dev/null 2>&1 && echo 'CLONE_OK'",
            "check": "CLONE_OK"
        },
        {
            "msg": "Ejecutando install.sh (esto tarda ~60 seg)...",
            "cmd": "cd /tmp/MaximusVpsMx && chmod +x install.sh && bash install.sh >/dev/null 2>&1 && echo 'INSTALL_OK'",
            "check": "INSTALL_OK"
        },
        {
            "msg": "Copiando licencia y desbloqueando panel en nodo esclavo...",
            "cmd": "_PLACEHOLDER_LICENSE_",
            "check": "LICENSE_OK"
        },
        {
            "msg": "Verificando API Multi-Nodo (puerto 6767)...",
            "cmd": "sleep 2 && curl -s http://127.0.0.1:6767/api/v1/health",
            "check": "ONLINE"
        }
    ]

    # Leer licencia del Master para copiarla al esclavo
    license_key = ""
    license_file = os.path.join(CONFIG_DIR, "license.key")
    if os.path.exists(license_file):
        with open(license_file, "r") as f:
            license_key = f.read().strip()

    # Construir el comando real para copiar licencia + key de nodo
    license_cmd = f"mkdir -p /etc/MaximusVpsMx && echo '{license_key}' > /etc/MaximusVpsMx/license.key"
    # Copiar token de API del Master
    api_token = "maximus_secret_node_key_2026"
    token_file = os.path.join(CONFIG_DIR, "api_token.conf")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            api_token = f.read().strip()
    license_cmd += f" && echo '{api_token}' > /etc/MaximusVpsMx/api_token.conf"
    # Reiniciar servicios
    license_cmd += " && systemctl restart maximus-node-api >/dev/null 2>&1"
    # NO crear .master_node — el esclavo NO debe tener el panel web (puerto 8080)
    license_cmd += " && systemctl stop maximus-master-web >/dev/null 2>&1; systemctl disable maximus-master-web >/dev/null 2>&1"
    license_cmd += " && echo 'LICENSE_OK'"

    # Reemplazar placeholder con comando real
    for step in steps:
        if step["cmd"] == "_PLACEHOLDER_LICENSE_":
            step["cmd"] = license_cmd

    for i, step in enumerate(steps):
        job["step"] = i + 1
        job["status"] = step["msg"]
        job["log"].append(f"[+] Paso {i+1}/{len(steps)}: {step['msg']}")

        try:
            code, output = _ssh_run(ip, port, user, password, step["cmd"])
            if step["check"] in output:
                job["log"].append(f"[OK] Paso {i+1} completado.")
            else:
                job["log"].append(f"[WARN] Paso {i+1} terminó con salida inesperada: {output[:120]}")
                if i == 0:
                    # Si falla la conexión SSH, abortar
                    job["error"] = True
                    job["done"] = True
                    job["status"] = f"ERROR: No se pudo conectar por SSH a {user}@{ip}:{port}"
                    job["log"].append(f"[ERROR] Fallo de conexión SSH: {output[:200]}")
                    return
        except subprocess.TimeoutExpired:
            job["log"].append(f"[WARN] Paso {i+1} excedió el timeout (300s).")
        except Exception as e:
            job["log"].append(f"[ERROR] Paso {i+1}: {str(e)}")

    # PASO FINAL: Sincronizar todos los usuarios existentes del Master al nuevo nodo
    job["status"] = "Sincronizando usuarios existentes al nuevo nodo..."
    job["log"].append(f"[+] Sincronizando usuarios del Master hacia {ip}...")
    synced = _sync_all_users_to_node(ip)
    job["log"].append(f"[OK] {synced} usuario(s) sincronizado(s) al nuevo nodo.")

    job["done"] = True
    job["status"] = "¡Instalación completada con éxito!"
    job["log"].append(f"[SUCCESS] ✅ VPS {ip} lista y sincronizada con {synced} usuarios.")

def _sync_all_users_to_node(node_ip):
    """Envía todos los usuarios del Master al nodo remoto vía API puerto 6767"""
    if not os.path.exists(USERS_DB):
        return 0

    api_token = "maximus_secret_node_key_2026"
    token_file = os.path.join(CONFIG_DIR, "api_token.conf")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            api_token = f.read().strip()

    user_requests = []
    with open(USERS_DB, "r") as f:
        for line in f:
            parts = line.strip().split(":")
            if len(parts) >= 3:
                username = parts[0].strip()
                password = parts[1].strip()
                exp_date = parts[2].strip()

                if not username or not password:
                    continue

                try:
                    exp = datetime.datetime.strptime(exp_date, "%Y-%m-%d").date()
                    days_left = (exp - datetime.date.today()).days
                    if days_left < 1:
                        days_left = 1
                except Exception:
                    days_left = 30

                user_requests.append((username, password, days_left))

    if not user_requests:
        return 0

    synced_count = [0]
    lock = threading.Lock()

    def _send_user(u, p, d):
        try:
            import urllib.request
            req_data = json.dumps({"username": u, "password": p, "days": d}).encode("utf-8")
            req = urllib.request.Request(
                f"http://{node_ip}:6767/api/v1/client/create",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-KEY": api_token
                }
            )
            resp = urllib.request.urlopen(req, timeout=5)
            with lock:
                synced_count[0] += 1
        except Exception as e:
            print(f"[Sync Error] Failed to send user {u} to node {node_ip}: {e}")

    threads = []
    for u, p, d in user_requests:
        t = threading.Thread(target=_send_user, args=(u, p, d))
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=6)

    print(f"[Sync Result] Node {node_ip}: {synced_count[0]}/{len(user_requests)} users synced.")
    return synced_count[0]

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
            # Siempre agregar el nodo local master al inicio
            nodes.append({
                "id": 1,
                "name": "Servidor Local (Master)",
                "ip": "127.0.0.1",
                "port": 22,
                "status": "ONLINE",
                "users": 1
            })
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 3:
                            if parts[1] in ["127.0.0.1", "localhost"]:
                                continue
                            nodes.append({
                                "id": _safe_hash(parts[1]),
                                "name": parts[0],
                                "ip": parts[1],
                                "port": int(parts[2]),
                                "status": "ONLINE",
                                "users": 1
                            })
            self._send_json(200, {"nodes": nodes})
            return

        if parsed.path == "/api/methods":
            load_mx_generator()
            methods = []
            if os.path.exists(METHODS_DB):
                with open(METHODS_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 8:
                            name = parts[0]
                            ssh_host = parts[1]
                            ssh_port = int(parts[2])
                            ssh_user = parts[3]
                            ssh_pass = parts[4]
                            protocol = parts[5]
                            sni = parts[6]
                            payload = parts[7]

                            mx_content = ""
                            if generate_mx_file:
                                try:
                                    mx_content = generate_mx_file(
                                        name=name,
                                        ssh_host=ssh_host,
                                        ssh_port=ssh_port,
                                        ssh_user=ssh_user,
                                        ssh_pass=ssh_pass,
                                        sni=sni,
                                        payload=payload
                                    )
                                except Exception as e:
                                    print(f"Error generating MX content: {e}")

                            methods.append({
                                "id": _safe_hash(name + ssh_host),
                                "name": name,
                                "ssh_host": ssh_host,
                                "ssh_port": ssh_port,
                                "ssh_user": ssh_user,
                                "ssh_pass": ssh_pass,
                                "protocol": protocol,
                                "sni": sni,
                                "payload": payload,
                                "mx_content": mx_content
                            })
                        elif len(parts) >= 5:
                            name = parts[0]
                            ssh_host = "127.0.0.1"
                            ssh_port = int(parts[4])
                            ssh_user = "root"
                            ssh_pass = ""
                            protocol = parts[1]
                            sni = parts[2]
                            payload = parts[3]

                            mx_content = ""
                            if generate_mx_file:
                                try:
                                    mx_content = generate_mx_file(
                                        name=name,
                                        ssh_host=ssh_host,
                                        ssh_port=ssh_port,
                                        ssh_user=ssh_user,
                                        ssh_pass=ssh_pass,
                                        sni=sni,
                                        payload=payload
                                    )
                                except Exception as e:
                                    print(f"Error generating MX content: {e}")

                            methods.append({
                                "id": _safe_hash(name),
                                "name": name,
                                "ssh_host": ssh_host,
                                "ssh_port": ssh_port,
                                "ssh_user": ssh_user,
                                "ssh_pass": ssh_pass,
                                "protocol": protocol,
                                "sni": sni,
                                "payload": payload,
                                "mx_content": mx_content
                            })
            self._send_json(200, {"methods": methods})
            return

        if parsed.path.startswith("/api/vps/install/status"):
            params = parse_qs(parsed.query)
            install_id = params.get("id", [""])[0]
            if install_id in _install_jobs:
                job = _install_jobs[install_id]
                self._send_json(200, {
                    "step": job["step"],
                    "total_steps": 6,
                    "status": job["status"],
                    "log": job["log"],
                    "done": job["done"],
                    "error": job.get("error", False)
                })
            else:
                self._send_json(404, {"error": "Install ID not found"})
            return

        # ----------------------------------------------------------------------
        # ARCHIVOS ESTÁTICOS DE LA WEB (index.html, style.css, app.js)
        # ----------------------------------------------------------------------
        file_path = parsed.path.lstrip("/")
        if not file_path:
            file_path = "index.html"

        # Regenerar archivo .mx al vuelo si no existe
        if file_path.startswith("downloads/") and file_path.endswith(".mx"):
            load_mx_generator()
            downloads_dir = os.path.join(WEB_DIR, "downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            full_file_path = os.path.join(WEB_DIR, file_path)
            
            if not os.path.exists(full_file_path):
                filename = os.path.basename(file_path)
                safe_name_req = filename[:-3] # Remover ".mx"
                
                # Intentar resolver/regenerar desde base de datos de métodos
                if os.path.exists(METHODS_DB):
                    import re
                    with open(METHODS_DB, "r") as f:
                        for line in f:
                            parts = line.strip().split("|")
                            if len(parts) >= 8:
                                name = parts[0]
                                safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
                                if safe_name == safe_name_req:
                                    if generate_mx_file:
                                        try:
                                            generate_mx_file(
                                                name=name,
                                                ssh_host=parts[1],
                                                ssh_port=int(parts[2]),
                                                ssh_user=parts[3],
                                                ssh_pass=parts[4],
                                                sni=parts[6],
                                                payload=parts[7],
                                                out_path=full_file_path
                                            )
                                        except Exception:
                                            pass
                                    break
                            elif len(parts) >= 5:
                                name = parts[0]
                                safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
                                if safe_name == safe_name_req:
                                    if generate_mx_file:
                                        try:
                                            generate_mx_file(
                                                name=name,
                                                ssh_host="127.0.0.1",
                                                ssh_port=int(parts[4]),
                                                ssh_user="root",
                                                ssh_pass="",
                                                sni=parts[2],
                                                payload=parts[3],
                                                out_path=full_file_path
                                            )
                                        except Exception:
                                            pass
                                    break

        full_file_path = os.path.join(WEB_DIR, file_path)
        if os.path.exists(full_file_path) and os.path.isfile(full_file_path):
            content_type = "text/html"
            if file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".mx"):
                content_type = "application/octet-stream"

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
        # POST /api/client/validate (VALIDACIÓN DE CREDENCIALES PARA LA APP)
        # ----------------------------------------------------------------------
        if parsed.path == "/api/client/validate":
            username = payload.get("username", "").strip().upper()
            password = payload.get("password", "").strip()

            if not username or not password:
                self._send_json(400, {"valid": False, "message": "Usuario y contraseña requeridos."})
                return

            valid = False
            exp_date = ""
            days_left = 0

            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) >= 3:
                            db_user = parts[0].upper()
                            db_pass = parts[1]
                            db_exp = parts[2]
                            if db_user == username and db_pass == password:
                                # Verificar que no esté vencido
                                try:
                                    exp = datetime.datetime.strptime(db_exp, "%Y-%m-%d").date()
                                    days_left = (exp - datetime.date.today()).days
                                    if days_left >= 0:
                                        valid = True
                                        exp_date = db_exp
                                except:
                                    pass
                                break

            if valid:
                self._send_json(200, {
                    "valid": True,
                    "username": username,
                    "exp_date": exp_date,
                    "days_left": days_left,
                    "message": "Acceso concedido."
                })
            else:
                self._send_json(200, {
                    "valid": False,
                    "message": "Usuario/contraseña incorrectos o cuenta vencida."
                })
            return

        # ----------------------------------------------------------------------
        # POST /api/client/create (CREACIÓN REAL EN LINUX)
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/client/create":
            username = payload.get("username", "").strip().upper()
            password = payload.get("password", "").strip()
            days = payload.get("days", 30)

            if not username or not password:
                self._send_json(400, {"error": "Username and password required"})
                return

            # 1. Crear localmente en este servidor VPS Master
            success, exp_date = execute_local_user_create(username, password, days)

            # 2. Replicar a otros nodos VPS guardados en nodes_servers.db
            api_token = "maximus_secret_node_key_2026"
            token_file = os.path.join(CONFIG_DIR, "api_token.conf")
            if os.path.exists(token_file):
                with open(token_file, "r") as f:
                    api_token = f.read().strip()

            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 2 and parts[1].strip() not in ["127.0.0.1", "localhost", ""]:
                            nip = parts[1].strip()
                            # Intentar enviar la orden por API al nodo remoto
                            try:
                                import urllib.request
                                req_data = json.dumps({"username": username, "password": password, "days": days}).encode("utf-8")
                                req = urllib.request.Request(f"http://{nip}:6767/api/v1/client/create", data=req_data, headers={
                                    "Content-Type": "application/json",
                                    "X-API-KEY": api_token
                                })
                                urllib.request.urlopen(req, timeout=5)
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
        # POST /api/vps/install (INSTALACIÓN REAL SSH REMOTA)
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/vps/install":
            name = payload.get("name", "VPS Remote")
            ip = payload.get("ip", "").strip()
            port = payload.get("port", 22)
            user = payload.get("user", "root")
            password = payload.get("password", "")

            # Guardar nodo en nodes_servers.db (evitando duplicados)
            exists = False
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 2 and parts[1] == ip:
                            exists = True
                            break
            if not exists:
                with open(NODES_DB, "a") as f:
                    f.write(f"{name}|{ip}|{port}\n")

            # Iniciar instalación real en un hilo de fondo
            install_id = f"{ip}_{int(time.time())}"
            _install_jobs[install_id] = {"status": "starting", "step": 0, "log": [], "done": False, "error": False}

            t = threading.Thread(target=_run_real_ssh_install, args=(install_id, ip, port, user, password), daemon=True)
            t.start()

            self._send_json(200, {
                "success": True,
                "install_id": install_id,
                "message": f"Instalación SSH REAL iniciada para {ip}."
            })
            return

        # ----------------------------------------------------------------------
        # POST /api/vps/delete
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/vps/delete":
            ip = payload.get("ip", "").strip()
            if not ip:
                self._send_json(400, {"error": "IP is required"})
                return

            lines = []
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    lines = f.readlines()

            with open(NODES_DB, "w") as f:
                for l in lines:
                    parts = l.strip().split("|")
                    if len(parts) >= 2 and parts[1] == ip:
                        continue
                    f.write(l)

            self._send_json(200, {"success": True, "message": f"VPS {ip} desvinculada."})
            return

        # ----------------------------------------------------------------------
        # POST /api/vps/sync
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/vps/sync":
            ip = payload.get("ip", "").strip()
            total_synced = 0

            if ip == "all" or not ip:
                # Sincronizar masivamente a TODOS los nodos guardados
                if os.path.exists(NODES_DB):
                    with open(NODES_DB, "r") as f:
                        for line in f:
                            parts = line.strip().split("|")
                            if len(parts) >= 2 and parts[1].strip() not in ["127.0.0.1", "localhost", ""]:
                                total_synced += _sync_all_users_to_node(parts[1].strip())
                self._send_json(200, {
                    "success": True,
                    "message": f"Sincronización masiva completada: {total_synced} envío(s) realizado(s) a todos los nodos."
                })
            else:
                total_synced = _sync_all_users_to_node(ip)
                self._send_json(200, {
                    "success": True,
                    "message": f"Sincronizados {total_synced} usuario(s) a la VPS {ip}."
                })
            return

        # ----------------------------------------------------------------------
        # POST /api/method/delete
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/method/delete":
            name = payload.get("name", "").strip()
            if not name:
                self._send_json(400, {"error": "Name is required"})
                return

            lines = []
            if os.path.exists(METHODS_DB):
                with open(METHODS_DB, "r") as f:
                    lines = f.readlines()

            with open(METHODS_DB, "w") as f:
                for l in lines:
                    parts = l.strip().split("|")
                    if len(parts) >= 1 and parts[0] == name:
                        continue
                    f.write(l)

            # Borrar archivo físico .mx
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
            mx_filename = f"{safe_name}.mx"
            mx_filepath = os.path.join(WEB_DIR, "downloads", mx_filename)
            if os.path.exists(mx_filepath):
                try:
                    os.remove(mx_filepath)
                except Exception:
                    pass

            self._send_json(200, {"success": True, "message": f"Método {name} y su archivo .mx eliminados."})
            return

        # ----------------------------------------------------------------------
        # POST /api/method/create
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/method/create":
            name = payload.get("name", "")
            ssh_host = payload.get("ssh_host", "").strip()
            ssh_port = payload.get("ssh_port", 22)
            # SSH User y SSH Pass vacíos para que la app móvil los pida manualmente
            ssh_user = ""
            ssh_pass = ""
            protocol = payload.get("protocol", "")
            sni = payload.get("sni", "")
            payload_str = payload.get("payload", "").strip()

            # Asegurar que el generador .MX esté cargado
            load_mx_generator()

            with open(METHODS_DB, "a") as f:
                f.write(f"{name}|{ssh_host}|{ssh_port}|{ssh_user}|{ssh_pass}|{protocol}|{sni}|{payload_str}\n")

            # Generar archivo físico .mx en la carpeta de descargas del panel web
            downloads_dir = os.path.join(WEB_DIR, "downloads")
            os.makedirs(downloads_dir, exist_ok=True)

            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
            mx_filename = f"{safe_name}.mx"
            mx_filepath = os.path.join(downloads_dir, mx_filename)

            if generate_mx_file:
                try:
                    generate_mx_file(
                        name=name,
                        ssh_host=ssh_host,
                        ssh_port=ssh_port,
                        ssh_user=ssh_user,
                        ssh_pass=ssh_pass,
                        sni=sni,
                        payload=payload_str,
                        out_path=mx_filepath
                    )
                except Exception as e:
                    print(f"Error writing physical MX file: {e}")

            self._send_json(200, {"success": True, "message": f"Método '{name}' guardado y archivo .mx generado."})
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
