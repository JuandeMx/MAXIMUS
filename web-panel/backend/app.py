from flask import Flask, request, jsonify, session, Response
import subprocess
import os
import datetime
import time
import json

# Configuración de Frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.secret_key = "maximus_ultra_secret_key_2026"

# Credenciales Admin
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

# Rutas de Archivos
USERS_DB = "/etc/MaximusVpsMx/users.db"
HYSTERIA_DB = "/etc/MaximusVpsMx/hysteria_users.db"

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except:
        return ""

def is_service_active(name):
    return subprocess.run(f"systemctl is-active --quiet {name}", shell=True).returncode == 0

def is_installed(name):
    """Chequea si un servicio/binario está instalado"""
    checks = {
        "ssh": "dpkg -l openssh-server 2>/dev/null | grep -q '^ii'",
        "dropbear": "dpkg -l dropbear 2>/dev/null | grep -q '^ii'",
        "ws-epro": "test -f /etc/systemd/system/ws-epro.service",
        "mx-proxy": "test -f /etc/systemd/system/mx-proxy.service",
        "stunnel4": "dpkg -l stunnel4 2>/dev/null | grep -q '^ii'",
        "badvpn": "test -f /usr/local/bin/badvpn-udpgw",
        "openvpn-server@server": "test -f /etc/openvpn/server/server.conf",
        "mx-slowdns": "test -f /etc/systemd/system/mx-slowdns.service",
        "udp-custom": "test -f /root/udp/udp-custom || test -f /etc/systemd/system/udp-custom.service",
        "hysteria": "test -f /etc/hysteria/hysteria",
        "x-ui": "test -f /usr/local/x-ui/x-ui",
        "mx-webpanel": "test -f /etc/systemd/system/mx-webpanel.service",
    }
    cmd = checks.get(name, f"test -f /etc/systemd/system/{name}.service")
    return subprocess.run(cmd, shell=True).returncode == 0

def get_port_for_service(name):
    ports = {
        "ssh": run_command("grep '^Port' /etc/ssh/sshd_config | awk '{print $2}' | head -1") or "22",
        "dropbear": run_command("grep 'DROPBEAR_PORT=' /etc/default/dropbear | cut -d= -f2 | tr -d '\"'") or "44",
        "stunnel4": run_command("grep 'accept =' /etc/stunnel/stunnel.conf | awk '{print $3}' | head -1") or "443",
        "mx-proxy": "80",
        "badvpn": "7300",
        "hysteria": "443/UDP",
        "udp-custom": "7100-7300",
        "ws-epro": "80",
        "openvpn-server@server": run_command("grep '^port ' /etc/openvpn/server/server.conf | awk '{print $2}'") or "1194",
        "x-ui": run_command("sqlite3 /etc/x-ui/x-ui.db \"SELECT value FROM settings WHERE key='webPort';\" 2>/dev/null") or "54321",
        "mx-slowdns": "53/UDP",
        "mx-webpanel": "8082",
    }
    return ports.get(name, "--")

def get_system_stats():
    ram_total = run_command("free -m | awk 'NR==2 {print $2}'")
    ram_used = run_command("free -m | awk 'NR==2 {print $3}'")
    ram_free = run_command("free -m | awk 'NR==2 {print $4}'")
    ram_cache = run_command("free -m | awk 'NR==2 {print $6}'")
    cpu_load = run_command("top -bn1 | grep 'Cpu(s)' | awk '{printf \"%.1f\", $2 + $4}'")
    cpu_cores = run_command("nproc")
    cpu_model = run_command("lscpu | grep 'Model name' | sed 's/.*: *//'")
    disk_total = run_command("df -h / | awk 'NR==2 {print $2}'")
    disk_used = run_command("df -h / | awk 'NR==2 {print $3}'")
    disk_free = run_command("df -h / | awk 'NR==2 {print $4}'")
    disk_perc = run_command("df -h / | awk 'NR==2 {print $5}'")
    net_rx = run_command("cat /proc/net/dev | grep eth0 | awk '{printf \"%.2f\", $2/1073741824}'")
    net_tx = run_command("cat /proc/net/dev | grep eth0 | awk '{printf \"%.2f\", $10/1073741824}'")
    uptime = run_command("uptime -p")
    load_avg = run_command("cat /proc/loadavg | awk '{print $1, $2, $3}'")
    online = run_command("netstat -antp 2>/dev/null | grep -E 'sshd|dropbear' | grep ESTABLISHED | wc -l")
    os_name = run_command("grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"'")
    kernel = run_command("uname -r")
    hostname = run_command("hostname")
    ip = run_command("wget -qO- ipv4.icanhazip.com 2>/dev/null") or "127.0.0.1"
    total_users = 0
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            total_users = sum(1 for line in f if line.strip())

    return {
        "ram": {"total": ram_total, "used": ram_used, "free": ram_free, "cache": ram_cache},
        "cpu": {"load": cpu_load, "cores": cpu_cores, "model": cpu_model},
        "disk": {"total": disk_total, "used": disk_used, "free": disk_free, "percent": disk_perc},
        "network": {"rx": net_rx, "tx": net_tx},
        "uptime": uptime, "load_avg": load_avg, "online": online,
        "system": {"os": os_name, "kernel": kernel, "hostname": hostname, "ip": ip},
        "total_users": total_users
    }

SERVICE_MAP = [
    {"id": "ssh", "name": "SSH", "icon": "fa-terminal", "desc": "Secure Shell", "installer": None},
    {"id": "dropbear", "name": "Dropbear", "icon": "fa-shield-halved", "desc": "Lightweight SSH", "installer": "install_dropbear.sh"},
    {"id": "ws-epro", "name": "WS-EPRO", "icon": "fa-globe", "desc": "WebSocket Proxy", "installer": "install_ws-epro.sh"},
    {"id": "mx-proxy", "name": "Python Proxy", "icon": "fa-code", "desc": "SOCKS Proxy", "installer": "install_mx-proxy.sh"},
    {"id": "stunnel4", "name": "Stunnel4 SSL", "icon": "fa-lock", "desc": "TLS/SSL Tunnel", "installer": "install_stunnel4.sh"},
    {"id": "badvpn", "name": "BadVPN UDPGW", "icon": "fa-satellite-dish", "desc": "UDP Gateway", "installer": "install_badvpn.sh"},
    {"id": "openvpn-server@server", "name": "OpenVPN", "icon": "fa-shield", "desc": "VPN Server", "installer": "install_openvpn.sh"},
    {"id": "mx-slowdns", "name": "SlowDNS", "icon": "fa-tower-broadcast", "desc": "DNS Tunnel", "installer": "install_slowdns.sh"},
    {"id": "udp-custom", "name": "UDP Custom", "icon": "fa-bolt", "desc": "Custom UDP", "installer": "install_udp-custom.sh"},
    {"id": "hysteria", "name": "Hysteria v2", "icon": "fa-rocket", "desc": "QUIC Protocol", "installer": "install_hysteria.sh"},
    {"id": "x-ui", "name": "X-UI Panel", "icon": "fa-table-columns", "desc": "Xray Panel", "installer": "install_xui.sh"},
    {"id": "mx-webpanel", "name": "Web Panel", "icon": "fa-display", "desc": "Este panel", "installer": "install_web-panel.sh"},
]

# ========== ROUTES ==========
@app.route('/')
def index():
    if 'logged_in' not in session:
        return app.send_static_file('login.html')
    return app.send_static_file('index.html')

@app.route('/login.html')
def login_page():
    return app.send_static_file('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        session['logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

@app.route('/api/logout')
def logout():
    session.pop('logged_in', None)
    return jsonify({"success": True})

# SSE Real-time
@app.route('/api/stream')
def stream():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    def generate():
        while True:
            data = get_system_stats()
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(2)
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/api/stats')
def stats():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    return jsonify(get_system_stats())

# ===== USERS =====
@app.route('/api/users/list')
def list_users():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    users = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 3:
                    expired = parts[2] < today
                    users.append({
                        "username": parts[0], "password": parts[1], "expiry": parts[2],
                        "type": "SSH/SSL", "status": "Expired" if expired else "Active",
                    })
    if os.path.exists(HYSTERIA_DB):
        with open(HYSTERIA_DB, "r") as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 3:
                    expired = parts[2] < today
                    users.append({
                        "username": parts[0], "password": parts[1], "expiry": parts[2],
                        "type": "Hysteria", "status": "Expired" if expired else "Active",
                    })
    return jsonify(users)

@app.route('/api/users/delete', methods=['POST'])
def delete_user():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    username = data.get('username')
    utype = data.get('type', 'SSH/SSL')
    if not username:
        return jsonify({"error": "Falta username"}), 400

    if utype == 'SSH/SSL':
        run_command(f"userdel -f {username} 2>/dev/null")
        run_command(f"pkill -u {username} 2>/dev/null")
        if os.path.exists(USERS_DB):
            with open(USERS_DB, "r") as f:
                lines = f.readlines()
            with open(USERS_DB, "w") as f:
                for line in lines:
                    if not line.startswith(f"{username}:"):
                        f.write(line)
    else:
        if os.path.exists(HYSTERIA_DB):
            with open(HYSTERIA_DB, "r") as f:
                lines = f.readlines()
            with open(HYSTERIA_DB, "w") as f:
                for line in lines:
                    if not line.startswith(f"{username}:"):
                        f.write(line)

    return jsonify({"success": True, "message": f"Usuario {username} eliminado"})

@app.route('/api/create/ssh', methods=['POST'])
def create_ssh():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    days = int(data.get('days', 3))
    limit = int(data.get('limit', 1))
    if not username or not password:
        return jsonify({"error": "Usuario y contraseña requeridos"}), 400
    check = run_command(f"id {username} 2>/dev/null")
    if check:
        return jsonify({"error": f"El usuario '{username}' ya existe"}), 400
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    run_command("rm -f /etc/passwd.lock /etc/shadow.lock")
    run_command(f"useradd -e {exp_date} -s /bin/false -M {username}")
    run_command(f"echo '{username}:{password}' | chpasswd")
    with open(USERS_DB, "a") as db:
        db.write(f"{username}:{password}:{exp_date}:{limit}\n")
    ip = run_command("wget -qO- ipv4.icanhazip.com 2>/dev/null") or "0.0.0.0"
    return jsonify({"success": True, "username": username, "password": password, "expiry": exp_date, "server_ip": ip})

@app.route('/api/create/hysteria', methods=['POST'])
def create_hysteria():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    days = int(data.get('days', 3))
    limit_down = data.get('limit_down', 100)
    limit_up = data.get('limit_up', 100)
    if not username or not password:
        return jsonify({"error": "Usuario y contraseña requeridos"}), 400
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    with open(HYSTERIA_DB, "a") as db:
        db.write(f"{username}:{password}:{exp_date}:{limit_up}:{limit_down}\n")
    ip = run_command("wget -qO- ipv4.icanhazip.com 2>/dev/null") or "0.0.0.0"
    obfs_val = run_command("grep 'password:' /etc/hysteria/config.yaml 2>/dev/null | tail -1 | awk '{print $NF}'") or "maximus"
    hy_port = run_command("grep 'listen:' /etc/hysteria/config.yaml 2>/dev/null | grep -o '[0-9]*' | head -1") or "443"
    link = f"hy2://{password}@{ip}:{hy_port}?insecure=1&sni=bing.com&obfs=salamander&obfs-password={obfs_val}#{username}"
    return jsonify({"success": True, "username": username, "password": password, "expiry": exp_date, "server_ip": ip, "link": link})

# ===== SERVICES =====
@app.route('/api/service/status')
def services_status():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    result = []
    for svc in SERVICE_MAP:
        installed = is_installed(svc["id"])
        active = is_service_active(svc["id"]) if installed else False
        port = get_port_for_service(svc["id"]) if active else "--"
        result.append({
            "id": svc["id"], "name": svc["name"], "icon": svc["icon"],
            "desc": svc["desc"], "active": active, "port": port,
            "installed": installed,
            "has_installer": svc["installer"] is not None,
        })
    return jsonify(result)

@app.route('/api/service/action', methods=['POST'])
def service_action():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    service_id = data.get('id')
    action = data.get('action')  # install, uninstall, start, stop, restart
    valid_ids = [s["id"] for s in SERVICE_MAP]
    if service_id not in valid_ids:
        return jsonify({"error": "Servicio no reconocido"}), 400

    svc_entry = next((s for s in SERVICE_MAP if s["id"] == service_id), None)

    if action == "install":
        installer = svc_entry.get("installer")
        if installer:
            path = f"/etc/MaximusVpsMx/modules/{installer}"
            if os.path.exists(path):
                run_command(f"bash {path}")
                time.sleep(2)
                return jsonify({"success": True, "message": f"{svc_entry['name']} instalación iniciada"})
            else:
                return jsonify({"error": "Módulo no encontrado"}), 400
        return jsonify({"error": "Sin instalador disponible"}), 400

    elif action == "uninstall":
        run_command(f"systemctl stop {service_id} 2>/dev/null")
        run_command(f"systemctl disable {service_id} 2>/dev/null")
        # Limpieza avanzada
        cleanup = {
            "stunnel4": "apt-get purge stunnel4 -y 2>/dev/null; rm -rf /etc/stunnel",
            "dropbear": "apt-get purge dropbear -y 2>/dev/null",
            "hysteria": "killall -9 hysteria 2>/dev/null; rm -rf /etc/hysteria",
            "udp-custom": "killall -9 udp-custom 2>/dev/null; rm -rf /root/udp",
            "x-ui": "systemctl stop x-ui; rm -rf /usr/local/x-ui /etc/x-ui /usr/bin/x-ui; rm -f /etc/systemd/system/x-ui.service",
        }
        if service_id in cleanup:
            run_command(cleanup[service_id])
        run_command("systemctl daemon-reload")
        time.sleep(1)
        return jsonify({"success": True, "message": f"{svc_entry['name']} desinstalado"})

    elif action in ("start", "stop", "restart"):
        run_command(f"systemctl {action} {service_id} 2>/dev/null")
        time.sleep(1)
        active = is_service_active(service_id)
        return jsonify({"success": True, "active": active})

    return jsonify({"error": "Acción no válida"}), 400

@app.route('/api/connections')
def active_connections():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    raw = run_command("netstat -antp 2>/dev/null | grep -E 'sshd|dropbear|stunnel|python3' | grep ESTABLISHED")
    connections = []
    for line in raw.split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 5:
                connections.append({
                    "proto": parts[0], "local": parts[3], "remote": parts[4],
                    "state": parts[5] if len(parts) > 5 else "ESTABLISHED",
                    "process": parts[-1] if len(parts) > 6 else "--"
                })
    return jsonify(connections)

# X-UI info
@app.route('/api/xui/info')
def xui_info():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    installed = is_installed("x-ui")
    active = is_service_active("x-ui") if installed else False
    port = get_port_for_service("x-ui") if installed else "--"
    ip = run_command("wget -qO- ipv4.icanhazip.com 2>/dev/null") or "0.0.0.0"
    return jsonify({
        "installed": installed, "active": active, "port": port, "ip": ip,
        "url": f"http://{ip}:{port}/" if installed else None,
        "cert_path": "/etc/x-ui/server.crt",
        "key_path": "/etc/x-ui/server.key",
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, threaded=True)
