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

# Autocargar e importar plantillas .LT al iniciar
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from preload_templates import import_all_plantillas
    import_all_plantillas()
except Exception as e_preload:
    print(f"[Preload Templates] Error autocargando plantillas: {e_preload}")

PORT = 8080
CONFIG_DIR = "/etc/MaximusVpsMx"
WEB_DIR = os.path.join(CONFIG_DIR, "web-panel")
USERS_DB = os.path.join(CONFIG_DIR, "users.db")
NODES_DB = os.path.join(CONFIG_DIR, "nodes_servers.db")
METHODS_DB = os.path.join(CONFIG_DIR, "connection_methods.db")
TEMPLATES_DB = os.path.join(CONFIG_DIR, "method_templates.db")

os.makedirs(CONFIG_DIR, exist_ok=True)

# Lista por defecto con las 7 configuraciones descifradas reales de tus archivos .LT
DEFAULT_7_METHODS = [
    "PERSONAL CF 1|Sat24.com|80|||SSL + Payload (WebSocket)|www.fahorro.com|MKCOL / HTTP/1.9[lf]Host: recargas.personal.com.ar[lf]Expect: 100-continue[crlf][crlf][split][crlf][crlf]GET- // HTTP/1.1[crlf]Host: [CF][crlf]Connection: Upgrade[crlf]User-Agent: [ua][crlf]Upgrade: websocket[crlf][crlf]",
    "PERSONAL CF 2|emailmarketing.personal.com.ar|80|||HTTP DIRECT / PAYLOAD||COPY / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][instant_split][lf][lf]X / HTTP/1.2[crlf]Host: recargas.personal.com.ar[crlf][lf][crlf]GET / HTTP/1.1[crlf]Host: [CF][crlf]Upgrade: websocket[crlf]Connection: Upgrade[crlf][crlf]",
    "PERSONAL CF 3|wap.renxo.com|80|||HTTP DIRECT / PAYLOAD||GET / HTTP/1.3[crlf]Host: rexo.personal.com.ar[crlf][crlf][crlf][split][crlf][split]GETT / HTTP/1.1[crlf]Host: [CF][crlf]Connection: Keep-Alive[crlf]Upgrade: websocket[crlf][crlf]",
    "PERSONAL CFT 1|recargas.personal.com.ar|80|||HTTP DIRECT / PAYLOAD||GET / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: [host][lf][lf]GET /suareznet HTTP/1.1[crlf]Host: [CFT][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf]",
    "PERSONAL CFT 2|institucional.telecom.com.ar|80|||HTTP DIRECT / PAYLOAD||HEAD / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: recargas.personal.com.ar[lf][lf]GET / HTTP/1.1[crlf]Host: [CFT][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf][split]",
    "PERSONAL CFT 3|device-api.smarthome.personal.com.ar|80|||HTTP DIRECT / PAYLOAD||HEAD / HTTP/1.1[crlf]Host: recargas.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: recargas.personal.com.ar[lf][lf]GET / HTTP/1.1[crlf]Host: [CFT][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf][split]",
    "PERSONAL CFT 4|www.personal.com.ar|80|||HTTP DIRECT / PAYLOAD||GET / HTTP/1.1[crlf]Host: emailmarketing.personal.com.ar[crlf][crlf][split][crlf][crlf]GET- / HTTP/1.1[crlf]Host: www.personal.com.ar[lf][lf]GET / HTTP/1.1[crlf]Host: [rotate=[CFT]][lf]Connection: Upgrade[lf]Upgrade: websocket[lf]User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html)[lf][lf][split]"
]

# Cargar o inicializar connection_methods.db solo si no existe o está vacío (respetando ediciones del usuario)
if not os.path.exists(METHODS_DB) or os.path.getsize(METHODS_DB) == 0:
    new_lines = [def_m + "\n" for def_m in DEFAULT_7_METHODS]
    with open(METHODS_DB, "w") as f:
        f.writelines(new_lines)
else:
    with open(METHODS_DB, "r") as f:
        new_lines = f.readlines()

# Autogenerar archivos .mx de descarga para los 7 métodos
downloads_dir = os.path.join(WEB_DIR, "downloads")
os.makedirs(downloads_dir, exist_ok=True)
import re

for line in new_lines:
    p = line.strip().split("|")
    if len(p) >= 8:
        name_m, host_m, port_m, _, _, proto_m, sni_m, pay_m = p[:8]
        safe_n = re.sub(r'[^a-zA-Z0-9_\-]', '_', name_m)
        mx_f = os.path.join(downloads_dir, f"{safe_n}.mx")
        load_mx_generator()
        if generate_mx_file:
            try:
                generate_mx_file(
                    name=name_m,
                    ssh_host=host_m,
                    ssh_port=int(port_m) if port_m.isdigit() else 80,
                    ssh_user="",
                    ssh_pass="",
                    sni=sni_m,
                    payload=pay_m,
                    out_path=mx_f
                )
            except Exception:
                pass

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

    # PASO FINAL: Generar métodos basados en plantillas para este nodo y sincronizar usuarios
    job["status"] = "Generando métodos de conexión para el nodo..."
    job["log"].append(f"[+] Compilando plantillas de conexión para {ip}...")
    methods_created = _compile_node_methods(ip)
    job["log"].append(f"[OK] {methods_created} método(s) autogenerado(s) para este nodo.")

    job["status"] = "Sincronizando usuarios existentes al nuevo nodo..."
    job["log"].append(f"[+] Sincronizando usuarios del Master hacia {ip}...")
    synced = _sync_all_users_to_node(ip)
    job["log"].append(f"[OK] {synced} usuario(s) sincronizado(s) al nuevo nodo.")

    job["done"] = True
    job["status"] = "¡Instalación completada con éxito!"
    job["log"].append(f"[SUCCESS] ✅ VPS {ip} lista y sincronizada con {synced} usuarios.")

def _compile_node_methods(node_ip):
    """Compila todas las plantillas globales en method_templates.db para una VPS específica usando sus dominios"""
    if not os.path.exists(NODES_DB) or not os.path.exists(TEMPLATES_DB):
        return 0

    node_data = None
    with open(NODES_DB, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 2 and parts[1].strip() == node_ip:
                node_name = parts[0].strip()
                n_port = parts[2].strip() if len(parts) > 2 else "22"
                domain_cf = parts[3].strip() if len(parts) > 3 else ""
                domain_cft = parts[4].strip() if len(parts) > 4 else ""
                node_data = (node_name, node_ip, n_port, domain_cf, domain_cft)
                break

    if not node_data:
        return 0

    node_name, nip, nport, cf_dom, cft_dom = node_data

    templates = []
    with open(TEMPLATES_DB, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 4:
                templates.append((parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()))

    if not templates:
        return 0

    # Leer métodos existentes para evitar duplicar
    existing_methods = set()
    if os.path.exists(METHODS_DB):
        with open(METHODS_DB, "r") as f:
            for line in f:
                parts = line.strip().split("|")
                if parts:
                    existing_methods.add(parts[0].strip())

    created_count = 0
    downloads_dir = os.path.join(WEB_DIR, "downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    for t_name, t_proto, t_sni, t_payload in templates:
        # Nombre exacto del archivo de la plantilla (sin corchetes ni sufijo .LT)
        final_method_name = t_name

        # Reemplazar variables dinámicas
        compiled_sni = t_sni.replace("[CF]", cf_dom).replace("[HOST]", cf_dom).replace("[CFT]", cft_dom).replace("[CLOUDFRONT]", cft_dom).replace("[IP]", nip)
        compiled_payload = t_payload.replace("[CF]", cf_dom).replace("[HOST]", cf_dom).replace("[CFT]", cft_dom).replace("[CLOUDFRONT]", cft_dom).replace("[IP]", nip)

        # Si no hay dominó CF/CFT configurado para la VPS, usar la IP
        if not compiled_sni or compiled_sni in ["[CF]", "[CFT]"]:
            compiled_sni = nip

        # Guardar o actualizar en connection_methods.db
        lines = []
        if os.path.exists(METHODS_DB):
            with open(METHODS_DB, "r") as f:
                lines = f.readlines()

        with open(METHODS_DB, "w") as f:
            for l in lines:
                if not l.startswith(f"{final_method_name}|"):
                    f.write(l)
            f.write(f"{final_method_name}|{nip}|{nport}|||{t_proto}|{compiled_sni}|{compiled_payload}\n")

        # Autogenerar archivo físico .MX
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', final_method_name)
        mx_filepath = os.path.join(downloads_dir, f"{safe_name}.mx")

        load_mx_generator()
        if generate_mx_file:
            try:
                generate_mx_file(
                    name=final_method_name,
                    ssh_host=nip,
                    ssh_port=int(nport),
                    ssh_user="",
                    ssh_pass="",
                    sni=compiled_sni,
                    payload=compiled_payload,
                    out_path=mx_filepath
                )
            except Exception:
                pass

        created_count += 1

    return created_count

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
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 2:
                            nodes.append({
                                "id": _safe_hash(parts[1].strip()),
                                "name": parts[0].strip(),
                                "ip": parts[1].strip(),
                                "port": int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 22,
                                "domain_cf": parts[3].strip() if len(parts) > 3 else "",
                                "domain_cft": parts[4].strip() if len(parts) > 4 else "",
                                "status": "ONLINE",
                                "users": 1
                            })

            # Si no hay ningún nodo guardado aún, crear por defecto la VPS Master
            if not nodes:
                host_header = self.headers.get("Host", "").split(":")[0]
                master_ip = host_header if host_header and host_header not in ["127.0.0.1", "localhost"] else "187.127.17.250"
                default_master = {
                    "id": 1,
                    "name": "Servidor Master (Brasil 1)",
                    "ip": master_ip,
                    "port": 22,
                    "domain_cf": "",
                    "domain_cft": "",
                    "status": "ONLINE",
                    "users": 1
                }
                nodes.append(default_master)
                # Guardar en NODES_DB para que sea totalmente editable
                with open(NODES_DB, "w") as f:
                    f.write(f"{default_master['name']}|{default_master['ip']}|22||\n")

            self._send_json(200, {"nodes": nodes})
            return

        if parsed.path == "/api/templates":
            templates = []
            if os.path.exists(TEMPLATES_DB):
                with open(TEMPLATES_DB, "r") as f:
                    for i, line in enumerate(f):
                        parts = line.strip().split("|")
                        if len(parts) >= 4:
                            templates.append({
                                "id": i + 1,
                                "name": parts[0],
                                "protocol": parts[1],
                                "sni": parts[2],
                                "payload": parts[3]
                            })
            self._send_json(200, {"templates": templates})
            return

        if parsed.path == "/api/methods":
            load_mx_generator()
            query_components = parse_qs(parsed.query)
            target_node_ip = query_components.get("node_ip", [""])[0].strip().lower()
            target_node_name = query_components.get("node_name", [""])[0].strip().lower()

            methods = []

            # 1. Leer todas las VPS/Nodos guardados
            nodes_list = []
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 2:
                            n_name = parts[0].strip()
                            n_ip = parts[1].strip()
                            n_port = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 22
                            d_cf = parts[3].strip() if len(parts) > 3 else ""
                            d_cft = parts[4].strip() if len(parts) > 4 else ""
                            if n_ip not in ["127.0.0.1", "localhost"]:
                                nodes_list.append((n_name, n_ip, n_port, d_cf, d_cft))

            # 2. Leer las 7 plantillas/métodos base
            base_methods = []
            if os.path.exists(METHODS_DB):
                with open(METHODS_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 8:
                            base_methods.append({
                                "name": parts[0].strip(),
                                "ssh_host": parts[1].strip(),
                                "ssh_port": int(parts[2].strip()) if parts[2].strip().isdigit() else 80,
                                "ssh_user": parts[3].strip(),
                                "ssh_pass": parts[4].strip(),
                                "protocol": parts[5].strip(),
                                "sni": parts[6].strip(),
                                "payload": parts[7].strip()
                            })

            # 3. Compilar métodos por cada VPS
            if nodes_list:
                for n_name, n_ip, n_port, d_cf, d_cft in nodes_list:
                    # Filtrar por IP o por Nombre de Servidor (ej: "Brasil 1" o "Mexico")
                    if target_node_ip and target_node_ip != n_ip.lower():
                        continue
                    if target_node_name and target_node_name not in n_name.lower():
                        continue

                    cf_val = d_cf if d_cf else n_ip
                    cft_val = d_cft if d_cft else n_ip

                    for bm in base_methods:
                        compiled_name = f"[{n_name}] {bm['name']}" if len(nodes_list) > 1 else bm['name']
                        compiled_sni = bm['sni']
                        compiled_payload = bm['payload']

                        # Usar el SSH Host del método (Sat24.com, wap.renxo.com, etc.), si está vacío usar la IP del nodo
                        final_host = bm['ssh_host'] if bm['ssh_host'] else n_ip
                        final_port = bm['ssh_port']

                        mx_content = ""
                        if generate_mx_file:
                            try:
                                mx_content = generate_mx_file(
                                    name=compiled_name,
                                    ssh_host=final_host,
                                    ssh_port=final_port,
                                    ssh_user="",
                                    ssh_pass="",
                                    sni=compiled_sni,
                                    payload=compiled_payload
                                )
                            except Exception:
                                pass

                        methods.append({
                            "id": _safe_hash(compiled_name + n_ip),
                            "name": compiled_name,
                            "ssh_host": final_host,
                            "ssh_port": final_port,
                            "ssh_user": "",
                            "ssh_pass": "",
                            "protocol": bm['protocol'],
                            "sni": compiled_sni,
                            "payload": compiled_payload,
                            "mx_content": mx_content,
                            "vps_name": n_name,
                            "vps_ip": n_ip
                        })
            else:
                for bm in base_methods:
                    mx_content = ""
                    if generate_mx_file:
                        try:
                            mx_content = generate_mx_file(
                                name=bm['name'],
                                ssh_host=bm['ssh_host'],
                                ssh_port=bm['ssh_port'],
                                ssh_user="",
                                ssh_pass="",
                                sni=bm['sni'],
                                payload=bm['payload']
                            )
                        except Exception:
                            pass

                    methods.append({
                        "id": _safe_hash(bm['name'] + bm['ssh_host']),
                        "name": bm['name'],
                        "ssh_host": bm['ssh_host'],
                        "ssh_port": bm['ssh_port'],
                        "ssh_user": "",
                        "ssh_pass": "",
                        "protocol": bm['protocol'],
                        "sni": bm['sni'],
                        "payload": bm['payload'],
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
            domain_cf = payload.get("domain_cf", "").strip()
            domain_cft = payload.get("domain_cft", "").strip()

            # Guardar nodo en nodes_servers.db (evitando duplicados)
            lines = []
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    lines = f.readlines()

            with open(NODES_DB, "w") as f:
                for l in lines:
                    parts = l.strip().split("|")
                    if len(parts) >= 2 and parts[1].strip() == ip:
                        continue
                    f.write(l)
                f.write(f"{name}|{ip}|{port}|{domain_cf}|{domain_cft}\n")

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
        # POST /api/vps/edit
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/vps/edit":
            original_ip = payload.get("original_ip", payload.get("ip", "")).strip()
            ip = payload.get("ip", "").strip()
            name = payload.get("name", "").strip()
            port = str(payload.get("port", 22)).strip()
            domain_cf = payload.get("domain_cf", "").strip()
            domain_cft = payload.get("domain_cft", "").strip()

            target_ip = original_ip if original_ip else ip
            if not target_ip:
                self._send_json(400, {"error": "IP is required"})
                return

            lines = []
            updated = False
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    lines = f.readlines()

            new_lines = []
            for l in lines:
                parts = l.strip().split("|")
                if len(parts) >= 2 and parts[1].strip() == target_ip:
                    new_name = name if name else parts[0].strip()
                    new_port = port if port else parts[2].strip()
                    new_ip = ip if ip else target_ip
                    new_lines.append(f"{new_name}|{new_ip}|{new_port}|{domain_cf}|{domain_cft}\n")
                    updated = True
                else:
                    new_lines.append(l)

            if not updated and name:
                new_lines.append(f"{name}|{ip}|{port}|{domain_cf}|{domain_cft}\n")

            with open(NODES_DB, "w") as f:
                f.writelines(new_lines)

            # Recompilar métodos autogenerados .MX
            _compile_node_methods(ip)

            self._send_json(200, {"success": True, "message": f"VPS {ip} actualizada correctamente."})
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
            name = payload.get("name", "").strip()
            ssh_host = payload.get("ssh_host", "").strip()
            ssh_port = payload.get("ssh_port", 80)
            ssh_user = ""
            ssh_pass = ""
            protocol = payload.get("protocol", "")
            sni = payload.get("sni", "").strip()
            payload_str = payload.get("payload", "").strip()

            if not name:
                self._send_json(400, {"error": "Name is required"})
                return

            load_mx_generator()

            lines = []
            if os.path.exists(METHODS_DB):
                with open(METHODS_DB, "r") as f:
                    lines = f.readlines()

            updated = False
            new_lines = []
            for l in lines:
                parts = l.strip().split("|")
                if parts and parts[0].strip() == name:
                    new_lines.append(f"{name}|{ssh_host}|{ssh_port}|{ssh_user}|{ssh_pass}|{protocol}|{sni}|{payload_str}\n")
                    updated = True
                else:
                    new_lines.append(l)

            if not updated:
                new_lines.append(f"{name}|{ssh_host}|{ssh_port}|{ssh_user}|{ssh_pass}|{protocol}|{sni}|{payload_str}\n")

            with open(METHODS_DB, "w") as f:
                f.writelines(new_lines)

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

        # ----------------------------------------------------------------------
        # POST /api/template/create (GUARDAR PLANTILLA Y REGENERAR MÉTODOS PARA NODOS)
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/template/create":
            name = payload.get("name", "").strip()
            protocol = payload.get("protocol", "SSH")
            sni = payload.get("sni", "").strip()
            payload_str = payload.get("payload", "").strip()

            if not name:
                self._send_json(400, {"error": "Name is required for template"})
                return

            lines = []
            if os.path.exists(TEMPLATES_DB):
                with open(TEMPLATES_DB, "r") as f:
                    lines = f.readlines()

            with open(TEMPLATES_DB, "w") as f:
                for l in lines:
                    if not l.startswith(f"{name}|"):
                        f.write(l)
                f.write(f"{name}|{protocol}|{sni}|{payload_str}\n")

            # Re-compilar métodos para todas las VPS registradas
            total_compiled = 0
            if os.path.exists(NODES_DB):
                with open(NODES_DB, "r") as f:
                    for l in f:
                        p = l.strip().split("|")
                        if len(p) >= 2:
                            total_compiled += _compile_node_methods(p[1].strip())

            self._send_json(200, {
                "success": True,
                "message": f"Plantilla '{name}' guardada. Se generaron {total_compiled} métodos para tus nodos VPS."
            })
            return

        # ----------------------------------------------------------------------
        # POST /api/template/delete
        # ----------------------------------------------------------------------
        elif parsed.path == "/api/template/delete":
            name = payload.get("name", "").strip()
            if name and os.path.exists(TEMPLATES_DB):
                lines = []
                with open(TEMPLATES_DB, "r") as f:
                    lines = f.readlines()
                with open(TEMPLATES_DB, "w") as f:
                    for l in lines:
                        if not l.startswith(f"{name}|"):
                            f.write(l)

            self._send_json(200, {"success": True, "message": f"Plantilla '{name}' eliminada."})
            return

        self._send_json(404, {"error": "Endpoint not found"})

def run():
    from http.server import ThreadingHTTPServer
    print(f"🚀 Maximus Master Web Backend Server running on http://0.0.0.0:{PORT} (Multi-Threaded)")
    server = ThreadingHTTPServer(("", PORT), MasterWebHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Master Web server...")
        server.server_close()

if __name__ == "__main__":
    run()
