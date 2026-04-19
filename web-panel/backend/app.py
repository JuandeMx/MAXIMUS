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

def get_cpu_info():
    """Lectura de bajo nivel de /proc/stat para carga de CPU real"""
    try:
        with open('/proc/stat', 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith('cpu '):
                fields = [float(column) for column in line.strip().split()[1:]]
                idle_time = fields[3]
                total_time = sum(fields)
                return idle_time, total_time
    except:
        return 0, 0

_prev_idle, _prev_total = get_cpu_info()

def get_real_cpu_usage():
    global _prev_idle, _prev_total
    idle, total = get_cpu_info()
    idle_delta = idle - _prev_idle
    total_delta = total - _prev_total
    _prev_idle, _prev_total = idle, total
    if total_delta == 0: return 0.0
    return round(100.0 * (1.0 - idle_delta / total_delta), 1)

def get_system_stats():
    # RAM via /proc/meminfo
    mem = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].split()[0])
        ram_total = mem.get('MemTotal', 0) // 1024
        ram_free = mem.get('MemFree', 0) // 1024
        ram_avail = mem.get('MemAvailable', 0) // 1024
        ram_used = ram_total - ram_avail
        ram_cache = (mem.get('Cached', 0) + mem.get('Buffers', 0)) // 1024
    except:
        ram_total = ram_free = ram_used = ram_cache = 0

    cpu_load = get_real_cpu_usage()
    cpu_cores = os.cpu_count() or 1
    cpu_model = run_command("lscpu | grep 'Model name' | sed 's/.*: *//'") or "CPU Genérica"
    
    # Red e IP
    iface = run_command("ip route show | grep default | awk '{print $5}'") or "eth0"
    net_rx = 0
    net_tx = 0
    try:
        with open('/proc/net/dev', 'r') as f:
            for line in f:
                if iface in line:
                    parts = line.split()
                    net_rx = round(int(parts[1]) / 1073741824, 2)
                    net_tx = round(int(parts[9]) / 1073741824, 2)
    except: pass

    disk_total = run_command("df -h / | awk 'NR==2 {print $2}'")
    disk_used = run_command("df -h / | awk 'NR==2 {print $3}'")
    disk_free = run_command("df -h / | awk 'NR==2 {print $4}'")
    disk_perc = run_command("df -h / | awk 'NR==2 {print $5}'")
    
    uptime = run_command("uptime -p")
    load_avg = run_command("cat /proc/loadavg | awk '{print $1, $2, $3}'")
    online = run_command("netstat -antp 2>/dev/null | grep ESTABLISHED | grep -v '127.0.0.1' | wc -l")
    
    os_name = run_command("grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"'")
    kernel = run_command("uname -r")
    hostname = run_command("hostname")
    ip = run_command("curl -s ipv4.icanhazip.com") or "127.0.0.1"

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
    {"id": "stunnel4", "name": "Stunnel4 SSL", "icon": "fa-lock", "desc": "TLS/SSL Tunnel", "installer": "install_stunnel4.sh"},
    {"id": "ws-epro", "name": "WS-EPRO", "icon": "fa-globe", "desc": "WebSocket Proxy", "installer": "install_ws-epro.sh"},
    {"id": "mx-proxy", "name": "Python Proxy", "icon": "fa-code", "desc": "SOCKS Proxy", "installer": "install_mx-proxy.sh"},
    {"id": "badvpn", "name": "BadVPN UDPGW", "icon": "fa-satellite-dish", "desc": "UDP Gateway", "installer": "install_badvpn.sh"},
    {"id": "openvpn-server@server", "name": "OpenVPN", "icon": "fa-shield", "desc": "VPN Server", "installer": "install_openvpn.sh"},
    {"id": "mx-slowdns", "name": "SlowDNS", "icon": "fa-tower-broadcast", "desc": "DNS Tunnel", "installer": "install_slowdns.sh"},
    {"id": "udp-custom", "name": "UDP Custom", "icon": "fa-bolt", "desc": "Custom UDP", "installer": "install_udp-custom.sh"},
    {"id": "hysteria", "name": "Hysteria v2", "icon": "fa-rocket", "desc": "QUIC Protocol", "installer": "install_hysteria.sh"},
    {"id": "x-ui", "name": "X-UI Panel", "icon": "fa-table-columns", "desc": "Xray Panel", "installer": "install_xui.sh"},
]

# ========== ROUTES ==========
@app.route('/')
def index():
    if 'logged_in' not in session:
        return app.send_static_file('login.html')
    return app.send_static_file('index.html')

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

@app.route('/api/stream')
def stream():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    def generate():
        while True:
            data = get_system_stats()
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(2)
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/api/stats')
def stats():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    return jsonify(get_system_stats())

# ===== USERS =====
@app.route('/api/users/list')
def list_users():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
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
                    except: days_left = 0
                    users.append({
                        "username": parts[0], "password": parts[1], "expiry": parts[2],
                        "status": "Expired" if expired else "Active", "days_left": days_left,
                        "limit": parts[3] if len(parts) >= 4 else "1"
                    })
    return jsonify(users)

@app.route('/api/users/renew', methods=['POST'])
def renew_user():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    data = request.json
    un, days = data.get('username'), int(data.get('days', 30))
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    run_command(f"chage -E {exp_date} {un}")
    # Actualizar DB
    if os.path.exists(USERS_DB):
        lines = open(USERS_DB).readlines()
        with open(USERS_DB, 'w') as f:
            for l in lines:
                p = l.strip().split(':')
                if p[0] == un: p[2] = exp_date; f.write(':'.join(p)+'\n')
                else: f.write(l)
    return jsonify({"success": True})

@app.route('/api/users/delete', methods=['POST'])
def delete_user():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    un = request.json.get('username')
    run_command(f"userdel -f {un}")
    if os.path.exists(USERS_DB):
        lines = open(USERS_DB).readlines()
        with open(USERS_DB, 'w') as f:
            for l in lines:
                if not l.startswith(f"{un}:"): f.write(l)
    return jsonify({"success": True})

# ===== TOOLS (Deep Integration) =====
@app.route('/api/tools/optimize', methods=['POST'])
def optimize_vps():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    cmd = "sync; echo 3 > /proc/sys/vm/drop_caches; swapoff -a && swapon -a; journalctl --vacuum-time=1d; apt-get clean; find /var/log -name '*.gz' -delete"
    res = run_command_full(cmd)
    return jsonify({"success": True, "log": [res['stdout'], res['stderr']]})

@app.route('/api/tools/banner', methods=['GET', 'POST'])
def handle_banner():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    if request.method == 'GET':
        banner = run_command("cat /etc/issue.net 2>/dev/null")
        return jsonify({"banner": banner})
    content = request.json.get('content', '')
    with open('/etc/issue.net', 'w') as f: f.write(content)
    return jsonify({"success": True})

@app.route('/api/tools/backup', methods=['POST'])
def tool_backup():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    run_command("tar -cvf /root/users_backup.tar /etc/passwd /etc/shadow /etc/MaximusVpsMx/users.db 2>/dev/null")
    size = run_command("du -h /root/users_backup.tar 2>/dev/null | awk '{print $1}'") or "0"
    return jsonify({"success": True, "path": "/root/users_backup.tar", "size": size})

@app.route('/api/tools/firewall', methods=['GET', 'POST'])
def tool_firewall():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    if request.method == 'GET':
        st = run_command("ufw status")
        return jsonify({"active": "active" in st.lower(), "raw": st})
    act = request.json.get('action')
    if act == 'enable': run_command("ufw allow 22/tcp; ufw allow 8082/tcp; ufw --force enable")
    elif act == 'disable': run_command("ufw disable")
    return jsonify({"success": True})

# ===== SERVICE ACTIONS =====
@app.route('/api/service/status')
def services_status():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    res = []
    for s in SERVICE_MAP:
        inst = is_installed(s["id"])
        act = is_service_active(s["id"]) if inst else False
        res.append({**s, "installed": inst, "active": act, "port": get_port_for_service(s["id"])})
    return jsonify(res)

@app.route('/api/service/action', methods=['POST'])
def service_action():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    sid, act = request.json.get('id'), request.json.get('action')
    if act in ("start", "stop", "restart"):
        run_command(f"systemctl {act} {sid}")
    elif act == "uninstall":
        run_command(f"systemctl stop {sid}; systemctl disable {sid}")
        # Lógica de limpieza profunda aquí...
    return jsonify({"success": True})

@app.route('/api/tools/exec', methods=['POST'])
def terminal_exec():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    data = request.json
    cmd = data.get('command', '')
    if not cmd:
        return jsonify({"error": "Comando vacío"}), 400
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
