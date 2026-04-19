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
    """Chequea si un servicio/binario está realmente instalado y configurado"""
    checks = {
        "ssh": "dpkg -l openssh-server 2>/dev/null | grep -q '^ii'",
        "dropbear": "test -f /etc/default/dropbear",
        "ws-epro": "test -f /etc/systemd/system/ws-epro.service",
        "mx-proxy": "test -f /etc/systemd/system/mx-proxy.service",
        "stunnel4": "test -f /etc/stunnel/stunnel.conf",
        "badvpn": "test -f /usr/local/bin/badvpn-udpgw",
        "openvpn-server@server": "test -f /etc/openvpn/server/server.conf",
        "mx-slowdns": "test -f /etc/systemd/system/mx-slowdns.service",
        "udp-custom": "test -f /etc/systemd/system/udp-custom.service",
        "hysteria": "test -x /etc/hysteria/hysteria 2>/dev/null || test -x /usr/local/bin/hysteria 2>/dev/null",
        "x-ui": "test -f /usr/local/x-ui/x-ui",
        "mx-webpanel": "systemctl list-unit-files | grep -q 'mx-webpanel.service'",
    }
    cmd = checks.get(name, f"systemctl list-unit-files | grep -q '{name}.service'")
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
    # Autodetección de interfaz de red principal
    iface = run_command("ip route show | grep default | awk '{print $5}'") or "eth0"
    
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
    
    # Tráfico usando la interfaz detectada
    net_rx = run_command(f"cat /proc/net/dev | grep {iface} | awk '{{printf \"%.2f\", $2/1073741824}}'")
    net_tx = run_command(f"cat /proc/net/dev | grep {iface} | awk '{{printf \"%.10f\", $10/1073741824}}'")
    
    uptime = run_command("uptime -p")
    load_avg = run_command("cat /proc/loadavg | awk '{print $1, $2, $3}'")
    
    # Conteo inteligente de usuarios (IPs Remotas Únicas conectadas a puertos de túnel)
    # Excluimos localhost (127.0.0.1) que son las conexiones internas del proxy
    online = run_command("netstat -antp 2>/dev/null | grep ESTABLISHED | grep -E ':22|:44|:80|:443|:8080|:8082' | awk '{print $5}' | cut -d: -f1 | sort -u | grep -v -E '127.0.0.1|0.0.0.0' | wc -l")
    
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
        "network": {"rx": net_rx, "tx": net_tx, "interface": iface},
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
    today = datetime.datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 3:
                    expired = parts[2] < today_str
                    try:
                        exp_dt = datetime.datetime.strptime(parts[2], "%Y-%m-%d")
                        days_left = max(0, (exp_dt - today).days)
                    except:
                        days_left = 0
                    limit = parts[3] if len(parts) >= 4 else "1"
                    hwid = parts[4] if len(parts) >= 5 else "OFF"
                    # Check if locked in system
                    lock_check = run_command(f"passwd -S {parts[0]} 2>/dev/null | awk '{{print $2}}'")
                    locked = lock_check in ("L", "LK")
                    users.append({
                        "username": parts[0], "password": parts[1], "expiry": parts[2],
                        "type": "SSH/SSL", "status": "Locked" if locked else ("Expired" if expired else "Active"),
                        "days_left": days_left, "limit": limit, "hwid": hwid,
                    })
    if os.path.exists(HYSTERIA_DB):
        with open(HYSTERIA_DB, "r") as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 3:
                    expired = parts[2] < today_str
                    try:
                        exp_dt = datetime.datetime.strptime(parts[2], "%Y-%m-%d")
                        days_left = max(0, (exp_dt - today).days)
                    except:
                        days_left = 0
                    users.append({
                        "username": parts[0], "password": parts[1], "expiry": parts[2],
                        "type": "Hysteria", "status": "Expired" if expired else "Active",
                        "days_left": days_left, "limit": "--", "hwid": "N/A",
                    })
    return jsonify(users)

@app.route('/api/users/renew', methods=['POST'])
def renew_user():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    username = data.get('username', '').strip()
    days = int(data.get('days', 3))
    if not username or days < 1:
        return jsonify({"error": "Datos inválidos"}), 400

    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            lines = f.readlines()
        updated = False
        new_lines = []
        for line in lines:
            parts = line.strip().split(':')
            if parts[0] == username:
                old_exp = parts[2]
                today = datetime.datetime.now()
                try:
                    old_dt = datetime.datetime.strptime(old_exp, "%Y-%m-%d")
                    base = old_dt if old_dt > today else today
                except:
                    base = today
                new_exp = (base + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
                parts[2] = new_exp
                new_lines.append(':'.join(parts) + '\n')
                run_command(f"chage -E {new_exp} {username} 2>/dev/null")
                updated = True
            else:
                new_lines.append(line)
        if updated:
            with open(USERS_DB, "w") as f:
                f.writelines(new_lines)
            return jsonify({"success": True, "new_expiry": new_exp})
    return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/api/users/change-password', methods=['POST'])
def change_password():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    username = data.get('username', '').strip()
    new_pass = data.get('password', '').strip()
    if not username or not new_pass:
        return jsonify({"error": "Datos incompletos"}), 400

    run_command(f"echo '{username}:{new_pass}' | chpasswd")
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            lines = f.readlines()
        with open(USERS_DB, "w") as f:
            for line in lines:
                parts = line.strip().split(':')
                if parts[0] == username and len(parts) >= 2:
                    parts[1] = new_pass
                    f.write(':'.join(parts) + '\n')
                else:
                    f.write(line)
    return jsonify({"success": True})

@app.route('/api/users/toggle-lock', methods=['POST'])
def toggle_lock():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    username = data.get('username', '').strip()
    if not username:
        return jsonify({"error": "Falta username"}), 400

    status = run_command(f"passwd -S {username} 2>/dev/null | awk '{{print $2}}'")
    if status in ("L", "LK"):
        run_command(f"usermod -U {username} 2>/dev/null")
        return jsonify({"success": True, "locked": False, "message": f"{username} desbloqueado"})
    else:
        run_command(f"usermod -L {username} 2>/dev/null")
        return jsonify({"success": True, "locked": True, "message": f"{username} bloqueado"})

@app.route('/api/users/purge-expired', methods=['POST'])
def purge_expired():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    removed = []
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            lines = f.readlines()
        keep = []
        for line in lines:
            parts = line.strip().split(':')
            if len(parts) >= 3 and parts[2] < today_str:
                run_command(f"userdel -f {parts[0]} 2>/dev/null")
                removed.append(parts[0])
            else:
                keep.append(line)
        with open(USERS_DB, "w") as f:
            f.writelines(keep)
    return jsonify({"success": True, "removed": removed, "count": len(removed)})

@app.route('/api/settings/credentials', methods=['POST'])
def change_credentials():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    global ADMIN_USER, ADMIN_PASS
    data = request.json
    new_user = data.get('username', '').strip()
    new_pass = data.get('password', '').strip()
    if not new_user or not new_pass:
        return jsonify({"error": "Campos vacíos"}), 400
    ADMIN_USER = new_user
    ADMIN_PASS = new_pass
    return jsonify({"success": True, "message": "Credenciales actualizadas (se aplicarán hasta reiniciar el panel)"})


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
    port = data.get('port', '')
    mode = data.get('mode', '')  # For stunnel: 1=direct, 2=proxy, 3=hybrid

    valid_ids = [s["id"] for s in SERVICE_MAP]
    if service_id not in valid_ids:
        return jsonify({"error": "Servicio no reconocido"}), 400

    svc_entry = next((s for s in SERVICE_MAP if s["id"] == service_id), None)

    if action == "install":
        installer = svc_entry.get("installer")
        if not installer:
            return jsonify({"error": "Sin instalador disponible"}), 400
        path = f"/etc/MaximusVpsMx/modules/{installer}"
        if not os.path.exists(path):
            return jsonify({"error": "Módulo no encontrado en el servidor"}), 400

        # Construct command with arguments based on service type
        if service_id == "stunnel4":
            # Stunnel needs: mode selection + port
            ssl_port = port or "443"
            stun_mode = mode or "1"
            cmd = f"echo -e '{stun_mode}\\n{ssl_port}' | bash {path}"
        elif service_id == "dropbear":
            drop_port = port or "44"
            cmd = f"echo '{drop_port}' | bash {path}"
        elif service_id == "badvpn":
            bad_port = port or "7300"
            cmd = f"echo '{bad_port}' | bash {path}"
        elif service_id == "mx-proxy":
            proxy_port = port or "80"
            cmd = f"bash {path} {proxy_port}"
        elif service_id == "openvpn-server@server":
            cmd = f"bash {path}"
        elif service_id == "hysteria":
            cmd = f"bash {path}"
        elif service_id == "udp-custom":
            cmd = f"bash {path}"
        elif service_id == "x-ui":
            cmd = f"bash {path}"
        else:
            cmd = f"bash {path}"

        # Run in background so it doesn't block the API
        run_command(f"nohup {cmd} > /tmp/mx_install_{service_id}.log 2>&1 &")
        time.sleep(3)
        active = is_service_active(service_id)
        return jsonify({"success": True, "active": active, "message": f"{svc_entry['name']} instalación ejecutada"})

    elif action == "uninstall":
        run_command(f"systemctl stop {service_id} 2>/dev/null")
        run_command(f"systemctl disable {service_id} 2>/dev/null")
        cleanup = {
            "stunnel4": "apt-get purge stunnel4 -y 2>/dev/null; rm -rf /etc/stunnel",
            "dropbear": "systemctl stop dropbear.socket 2>/dev/null; apt-get purge dropbear -y 2>/dev/null",
            "hysteria": "killall -9 hysteria 2>/dev/null; rm -rf /etc/hysteria",
            "udp-custom": "killall -9 udp-custom 2>/dev/null; rm -rf /root/udp; rm -f /etc/systemd/system/udp-custom.service",
            "x-ui": "systemctl stop x-ui; rm -rf /usr/local/x-ui /etc/x-ui /usr/bin/x-ui; rm -f /etc/systemd/system/x-ui.service",
            "badvpn": "rm -f /etc/systemd/system/badvpn.service",
            "mx-proxy": "rm -f /etc/systemd/system/mx-proxy.service",
            "ws-epro": "rm -f /etc/systemd/system/ws-epro.service",
            "mx-slowdns": "rm -f /etc/systemd/system/mx-slowdns.service",
        }
        if service_id in cleanup:
            run_command(cleanup[service_id])
        run_command("systemctl daemon-reload")
        time.sleep(1)
        return jsonify({"success": True, "message": f"{svc_entry['name']} desinstalado"})

    elif action == "change-port":
        # Change port for running service
        new_port = port
        if not new_port:
            return jsonify({"error": "Puerto no especificado"}), 400

        if service_id == "dropbear":
            run_command(f"sed -i 's/DROPBEAR_PORT=.*/DROPBEAR_PORT={new_port}/' /etc/default/dropbear")
            run_command(f"ufw allow {new_port}/tcp 2>/dev/null")
            run_command("systemctl restart dropbear")
        elif service_id == "stunnel4":
            run_command(f"sed -i 's/accept = .*/accept = {new_port}/' /etc/stunnel/stunnel.conf")
            run_command(f"ufw allow {new_port}/tcp 2>/dev/null")
            run_command("systemctl restart stunnel4")
        elif service_id == "ssh":
            run_command(f"sed -i 's/^Port .*/Port {new_port}/' /etc/ssh/sshd_config")
            run_command(f"ufw allow {new_port}/tcp 2>/dev/null")
            run_command("systemctl restart ssh")
        elif service_id == "badvpn":
            run_command(f"sed -i 's/--listen-addr 127.0.0.1:[0-9]*/--listen-addr 127.0.0.1:{new_port}/' /etc/systemd/system/badvpn.service")
            run_command("systemctl daemon-reload")
            run_command("systemctl restart badvpn")
        elif service_id == "x-ui":
            run_command(f"/usr/local/x-ui/x-ui setting -port {new_port} >/dev/null 2>&1")
            run_command(f"ufw allow {new_port}/tcp 2>/dev/null")
            run_command("systemctl restart x-ui")

        time.sleep(1)
        active = is_service_active(service_id)
        return jsonify({"success": True, "active": active, "port": new_port})

    elif action in ("start", "stop", "restart"):
        if action == "start":
            run_command(f"systemctl enable --now {service_id} 2>/dev/null")
        else:
            run_command(f"systemctl {action} {service_id} 2>/dev/null")
        time.sleep(1)
        active = is_service_active(service_id)
        return jsonify({"success": True, "active": active})

    return jsonify({"error": "Acción no válida"}), 400


@app.route('/api/service/info/<service_id>')
def service_info(service_id):
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401

    info = {"id": service_id}

    if service_id == "mx-slowdns":
        ns_domain = run_command("cat /etc/MaximusVpsMx/slowdns/ns-domain.conf 2>/dev/null") or "no configurado"
        pub_key = run_command("cat /etc/MaximusVpsMx/slowdns/server.pub 2>/dev/null") or ""
        info["ns_domain"] = ns_domain.strip()
        info["public_key"] = pub_key.strip()
        info["installed"] = is_installed("mx-slowdns")
        info["active"] = is_service_active("mx-slowdns")

    elif service_id == "x-ui":
        ip = run_command("wget -qO- ipv4.icanhazip.com 2>/dev/null") or "0.0.0.0"
        port = get_port_for_service("x-ui")
        info["ip"] = ip
        info["port"] = port
        info["url"] = f"http://{ip}:{port}/"
        info["cert_path"] = "/etc/x-ui/server.crt"
        info["key_path"] = "/etc/x-ui/server.key"
        info["installed"] = is_installed("x-ui")
        info["active"] = is_service_active("x-ui")

    elif service_id == "stunnel4":
        conf = run_command("cat /etc/stunnel/stunnel.conf 2>/dev/null") or ""
        info["config_preview"] = conf[:500]
        info["installed"] = is_installed("stunnel4")
        info["active"] = is_service_active("stunnel4")

    else:
        # Generic: return last 10 lines of install log
        log = run_command(f"tail -n 10 /tmp/mx_install_{service_id}.log 2>/dev/null") or ""
        info["log"] = log
        info["installed"] = is_installed(service_id)
        info["active"] = is_service_active(service_id)

    return jsonify(info)

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

# ========== HERRAMIENTAS DE SISTEMA (Réplica exacta del MX terminal) ==========

def run_command_full(cmd):
    """Ejecuta comando y retorna stdout + stderr + exit code para log de consola"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "TIMEOUT: Comando excedió 60s", "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}

@app.route('/api/tools/optimize', methods=['POST'])
def optimize_vps():
    """Réplica exacta de MX opción 1 en menu_sistema: sync; drop_caches; swap; journal; apt clean; logs"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    log = []
    # 1. Sync y dropear caches del kernel
    r = run_command_full("sync; echo 3 > /proc/sys/vm/drop_caches")
    log.append(f"[drop_caches] exit={r['exit_code']}")
    # 2. Reset swap
    r = run_command_full("swapoff -a 2>/dev/null; swapon -a 2>/dev/null")
    log.append(f"[swap reset] exit={r['exit_code']}")
    # 3. Vacuum journalctl (solo 1 día)
    r = run_command_full("journalctl --vacuum-time=1d 2>/dev/null")
    log.append(f"[journal vacuum] {r['stdout'][:100]}")
    # 4. APT clean
    r = run_command_full("apt-get clean 2>/dev/null")
    log.append(f"[apt clean] exit={r['exit_code']}")
    # 5. Eliminar logs rotados
    r = run_command_full("find /var/log -type f -name '*.gz' -delete; find /var/log -type f -name '*.[0-9]' -delete")
    log.append(f"[log cleanup] exit={r['exit_code']}")
    # Estado post-optimización
    ram_free = run_command("free -m | awk 'NR==2 {print $4}'")
    log.append(f"[RAM libre post-optimización] {ram_free} MB")
    return jsonify({"success": True, "log": log})

@app.route('/api/tools/backup', methods=['POST'])
def backup_users():
    """Réplica de MX opción 3: tar -cvf /root/users_backup.tar passwd shadow users.db"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    r = run_command_full("tar -cvf /root/users_backup.tar /etc/passwd /etc/shadow /etc/MaximusVpsMx/users.db 2>/dev/null")
    exists = os.path.exists("/root/users_backup.tar") if True else False
    size = run_command("du -h /root/users_backup.tar 2>/dev/null | awk '{print $1}'") or "0"
    return jsonify({
        "success": r["exit_code"] == 0,
        "path": "/root/users_backup.tar",
        "size": size,
        "log": r["stdout"].split('\n') if r["stdout"] else [],
        "error": r["stderr"] if r["exit_code"] != 0 else ""
    })

@app.route('/api/tools/banner', methods=['GET'])
def get_banner():
    """Lee el banner actual de /etc/issue.net"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    banner = run_command("cat /etc/issue.net 2>/dev/null") or ""
    return jsonify({"banner": banner})

@app.route('/api/tools/banner', methods=['POST'])
def set_banner():
    """Escribe el banner en /etc/issue.net (el mismo archivo que edita nano en MX opción 2)"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    content = data.get('content', '')
    try:
        with open('/etc/issue.net', 'w') as f:
            f.write(content)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tools/traffic')
def traffic_monitor():
    """Réplica de MX opción 4: vnstat + lectura directa de /proc/net/dev"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    iface = run_command("ip route show | grep default | awk '{print $5}'") or "eth0"
    # vnstat summary (si está instalado)
    vnstat_out = run_command("vnstat --json 2>/dev/null")
    vnstat_data = None
    if vnstat_out:
        try:
            vnstat_data = json.loads(vnstat_out)
        except:
            pass
    # Lectura directa de /proc/net/dev (siempre disponible)
    raw = run_command(f"cat /proc/net/dev | grep {iface}")
    rx_bytes = tx_bytes = 0
    if raw:
        parts = raw.split()
        if len(parts) >= 10:
            rx_bytes = int(parts[1])
            tx_bytes = int(parts[9])
    # Tráfico por usuario (netstat)
    per_user = run_command(
        "netstat -antp 2>/dev/null | grep ESTABLISHED | grep -E ':22|:44|:80|:443' | "
        "awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10"
    )
    user_traffic = []
    for line in (per_user or "").split('\n'):
        line = line.strip()
        if line:
            parts = line.split()
            if len(parts) >= 2:
                user_traffic.append({"connections": int(parts[0]), "ip": parts[1]})

    return jsonify({
        "interface": iface,
        "rx_bytes": rx_bytes, "tx_bytes": tx_bytes,
        "rx_gb": round(rx_bytes / 1073741824, 2),
        "tx_gb": round(tx_bytes / 1073741824, 2),
        "vnstat": vnstat_data,
        "top_ips": user_traffic
    })

@app.route('/api/tools/firewall')
def firewall_status():
    """Lee el estado real de UFW"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    status = run_command("ufw status 2>/dev/null")
    active = "active" in (status or "").lower() and "inactive" not in (status or "").lower()
    # Parsear reglas
    rules = []
    for line in (status or "").split('\n'):
        line = line.strip()
        if line and not line.startswith('Status') and not line.startswith('To') and not line.startswith('--'):
            rules.append(line)
    return jsonify({"active": active, "rules": rules, "raw": status})

@app.route('/api/tools/firewall', methods=['POST'])
def firewall_action():
    """Acciones reales sobre UFW: enable, disable, allow, delete"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    action = data.get('action')  # enable, disable, allow, delete
    port = data.get('port', '')
    proto = data.get('proto', 'tcp')

    if action == 'enable':
        # Igual que MX: primero permitir puertos críticos, luego activar
        r = run_command_full("ufw allow 22,44,80,443/tcp 2>/dev/null; ufw --force enable")
        return jsonify({"success": True, "log": r["stdout"], "error": r["stderr"]})
    elif action == 'disable':
        r = run_command_full("ufw disable")
        return jsonify({"success": True, "log": r["stdout"]})
    elif action == 'allow':
        if not port:
            return jsonify({"error": "Puerto requerido"}), 400
        r = run_command_full(f"ufw allow {port}/{proto} 2>/dev/null")
        return jsonify({"success": r["exit_code"] == 0, "log": r["stdout"], "error": r["stderr"]})
    elif action == 'delete':
        if not port:
            return jsonify({"error": "Puerto requerido"}), 400
        r = run_command_full(f"ufw delete allow {port}/{proto} 2>/dev/null")
        return jsonify({"success": r["exit_code"] == 0, "log": r["stdout"], "error": r["stderr"]})
    return jsonify({"error": "Acción no válida"}), 400

@app.route('/api/tools/cloudflare', methods=['GET'])
def cloudflare_get():
    """Lee la configuración actual de Cloudflare DDNS"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    conf_path = "/etc/MaximusVpsMx/cloudflare.conf"
    config = {"token": "", "zone_id": "", "record": "", "active": False}
    if os.path.exists(conf_path):
        content = run_command(f"cat {conf_path}")
        for line in (content or "").split('\n'):
            if 'CF_API_TOKEN=' in line:
                config["token"] = line.split('=', 1)[1].strip().strip('"')
            elif 'CF_ZONE_ID=' in line:
                config["zone_id"] = line.split('=', 1)[1].strip().strip('"')
            elif 'CF_RECORD_NAME=' in line:
                config["record"] = line.split('=', 1)[1].strip().strip('"')
    # Verificar si el cron está activo
    cron = run_command("crontab -l 2>/dev/null | grep cloudflare-ddns")
    config["active"] = bool(cron)
    return jsonify(config)

@app.route('/api/tools/cloudflare', methods=['POST'])
def cloudflare_action():
    """Configurar, activar o desactivar Cloudflare DDNS (réplica MX opción 6)"""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    action = data.get('action')  # save, enable, disable

    if action == 'save':
        token = data.get('token', '').strip()
        zone_id = data.get('zone_id', '').strip()
        record = data.get('record', '').strip()
        if not token or not zone_id or not record:
            return jsonify({"error": "Todos los campos son requeridos"}), 400
        run_command("mkdir -p /etc/MaximusVpsMx")
        conf = f'CF_API_TOKEN="{token}"\nCF_ZONE_ID="{zone_id}"\nCF_RECORD_NAME="{record}"\n'
        try:
            with open("/etc/MaximusVpsMx/cloudflare.conf", "w") as f:
                f.write(conf)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif action == 'enable':
        r = run_command_full(
            '(crontab -l 2>/dev/null | grep -v "cloudflare-ddns"; '
            'echo "*/5 * * * * /etc/MaximusVpsMx/modules/cloudflare-ddns.sh") | crontab -'
        )
        return jsonify({"success": r["exit_code"] == 0, "log": r["stdout"], "error": r["stderr"]})

    elif action == 'disable':
        r = run_command_full('crontab -l 2>/dev/null | grep -v "cloudflare-ddns" | crontab -')
        return jsonify({"success": True})

    return jsonify({"error": "Acción no válida"}), 400

@app.route('/api/tools/exec', methods=['POST'])
def exec_log():
    """Endpoint de auditoría: ejecuta un comando y devuelve stdout+stderr+exit_code.
    Solo para diagnóstico administrativo."""
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    data = request.json
    cmd = data.get('cmd', '')
    if not cmd:
        return jsonify({"error": "Comando vacío"}), 400
    # Lista blanca de comandos seguros
    safe_prefixes = [
        'systemctl status', 'systemctl is-active', 'cat /etc/', 'tail ',
        'head ', 'ufw status', 'netstat', 'ss ', 'free ', 'df ', 'uptime',
        'vnstat', 'whoami', 'id ', 'ls ', 'wc ', 'grep ', 'awk '
    ]
    allowed = any(cmd.strip().startswith(p) for p in safe_prefixes)
    if not allowed:
        return jsonify({"error": "Comando no permitido por seguridad"}), 403
    r = run_command_full(cmd)
    return jsonify(r)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, threaded=True)
