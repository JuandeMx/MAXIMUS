from flask import Flask, request, jsonify, session, Response
import subprocess
import os
import datetime
import time
import json

# ==========================================
# MAXIMUS WEB PANEL v3.1 (CORE RESET)
# ==========================================

app = Flask(__name__, static_folder="../frontend", static_url_path='')
app.secret_key = "maximus_ultra_secret_v3"

ADMIN_USER = "admin"
ADMIN_PASS = "admin"
USERS_DB = "/etc/MaximusVpsMx/users.db"

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip()
    except: return ""

def run_install_command(cmd):
    """Función dedicada para instalaciones largas sin matar el proceso"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return result.stdout.strip()
    except: return "TIMEOUT"

def run_command_full(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "code": result.returncode
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "code": 1}

def is_installed(name):
    checks = {
        "ssh": "dpkg -l openssh-server 2>/dev/null | grep -q '^ii'",
        "dropbear": "test -f /etc/default/dropbear",
        "ws-epro": "test -f /etc/systemd/system/ws-epro.service",
        "mx-proxy": "test -f /etc/systemd/system/mx-proxy.service",
        "stunnel4": "test -f /etc/stunnel/stunnel.conf",
        "badvpn": "test -f /usr/local/bin/badvpn-udpgw",
        "x-ui": "test -f /usr/local/x-ui/x-ui",
    }
    cmd = checks.get(name, f"systemctl list-unit-files | grep -q '{name}.service'")
    return subprocess.run(cmd, shell=True).returncode == 0

def is_service_active(name):
    if name == "ssh": name = "sshd"
    return subprocess.run(f"systemctl is-active --quiet {name}", shell=True).returncode == 0

def get_port_for_service(name):
    ports = {
        "ssh": run_command("grep -E '^#?Port [0-9]+' /etc/ssh/sshd_config | awk '{print $2}' | head -1") or "22",
        "dropbear": run_command("grep 'DROPBEAR_PORT=' /etc/default/dropbear 2>/dev/null | cut -d= -f2 | tr -d '\"'") or "44",
        "stunnel4": run_command("grep 'accept =' /etc/stunnel/stunnel.conf 2>/dev/null | awk '{print $3}' | head -1") or "443",
        "mx-proxy": run_command("grep 'ExecStart=' /etc/systemd/system/mx-proxy.service 2>/dev/null | awk '{print $NF}' | sed 's/-//g'") or "80",
        "badvpn": "7300",
        "ws-epro": "80",
        "udp-custom": run_command("iptables -t nat -L PREROUTING -n | grep ':36712' | awk '{print $7}' | awk -F: '{print $NF}' | head -1") or "7100:7300",
        "hysteria": run_command("iptables -t nat -L PREROUTING -n | grep ':36713' | awk '{print $7}' | awk -F: '{print $NF}' | head -1") or "2000:5000",
        "mx-slowdns": "53/UDP",
    }
    return ports.get(name, "--")

SERVICE_MAP = [
    {"id": "ssh", "name": "SSH", "icon": "fa-terminal", "desc": "Acceso Principal Secure Shell"},
    {"id": "dropbear", "name": "Dropbear", "icon": "fa-shield-halved", "desc": "SSH de bajo consumo"},
    {"id": "stunnel4", "name": "Stunnel4", "icon": "fa-lock", "desc": "Túnel SSL/TLS"},
    {"id": "ws-epro", "name": "WS-EPRO", "icon": "fa-globe", "desc": "WebSocket Proxy Python"},
    {"id": "mx-proxy", "name": "Python Proxy", "icon": "fa-code", "desc": "Proxy HTTP Custom"},
    {"id": "badvpn", "name": "BadVPN", "icon": "fa-satellite-dish", "desc": "UDP Gateway para Juegos"},
    {"id": "mx-slowdns", "name": "SlowDNS", "icon": "fa-tower-broadcast", "desc": "Túnel DNS over UDP"},
    {"id": "udp-custom", "name": "UDP Custom", "icon": "fa-bolt", "desc": "Protocolo UDP Optimizado"}
]


# --- Telemetría de Bajo Nivel (Lectura Directa) ---

def get_cpu_raw():
    try:
        with open('/proc/stat', 'r') as f:
            for line in f:
                if line.startswith('cpu '):
                    fields = [float(column) for column in line.strip().split()[1:]]
                    return fields[3], sum(fields)
    except: return 0, 0

_prev_idle, _prev_total = get_cpu_raw()

def get_cpu_usage():
    global _prev_idle, _prev_total
    idle, total = get_cpu_raw()
    idle_delta = idle - _prev_idle
    total_delta = total - _prev_total
    _prev_idle, _prev_total = idle, total
    if total_delta <= 0: return 0.0
    return round(100.0 * (1.0 - idle_delta / total_delta), 1)

def get_stats():
    # RAM
    mem = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                p = line.split(':')
                if len(p) == 2: mem[p[0].strip()] = int(p[1].split()[0])
        total_ram = mem.get('MemTotal', 1) // 1024
        free_ram = mem.get('MemAvailable', mem.get('MemFree', 0)) // 1024
        used_ram = total_ram - free_ram
    except: total_ram = used_ram = 0

    # DISCO
    try:
        df = run_command("df -h / | awk 'NR==2 {print $2, $3, $5}'").split()
        d_total, d_used, d_perc = df[0], df[1], df[2].replace('%','')
    except: d_total, d_used, d_perc = "--", "--", "0"

    # RED (Tráfico)
    iface = run_command("ip route show | grep default | awk '{print $5}'") or "eth0"
    rx = tx = 0
    try:
        with open('/proc/net/dev', 'r') as f:
            for line in f:
                if iface in line:
                    parts = line.split()
                    rx = round(int(parts[1]) / 1073741824, 2) # GB
                    tx = round(int(parts[9]) / 1073741824, 2)
    except: pass

    # Usuarios
    total_u = 0
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f: total_u = sum(1 for line in f if line.strip())

    return {
        "cpu": {"load": get_cpu_usage(), "cores": os.cpu_count() or 1, "model": run_command("lscpu | grep 'Model name' | head -1 | cut -d: -f2").strip()},
        "ram": {"total": total_ram, "used": used_ram, "percent": round((used_ram/total_ram*100),1) if total_ram > 0 else 0},
        "disk": {"total": d_total, "used": d_used, "percent": d_perc},
        "net": {"rx": rx, "tx": tx, "iface": iface},
        "sys": {
            "hostname": run_command("hostname"),
            "kernel": run_command("uname -r"),
            "os": run_command("grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"'"),
            "uptime": run_command("uptime -p"),
            "ip": run_command("curl -s ipv4.icanhazip.com") or "127.0.0.1"
        },
        "online": run_command("netstat -antp | grep ESTABLISHED | grep -v '127.0.0.1' | wc -l") or "0",
        "total_users": total_u,
        "ts": int(time.time())
    }

# ========== ROUTES ==========

@app.route('/')
def index():
    if 'auth' not in session: return app.send_static_file('login.html')
    return app.send_static_file('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    # Ajuste para coincidir con login.html (username/password)
    if d.get('username') == ADMIN_USER and d.get('password') == ADMIN_PASS:
        session['auth'] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route('/api/stats')
def api_stats():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_stats())

@app.route('/api/stream')
def stream():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    def gen():
        while True:
            yield f"data: {json.dumps(get_stats())}\n\n"
            time.sleep(2)
    return Response(gen(), mimetype='text/event-stream', headers={'X-Accel-Buffering': 'no'})


# ====== USUARIOS ======

@app.route('/api/users/list')
def list_users():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    users = []
    if os.path.exists(USERS_DB):
        today = datetime.datetime.now()
        with open(USERS_DB, "r") as f:
            for line in f:
                p = line.strip().split(':')
                if len(p) >= 3:
                    try:
                        exp = datetime.datetime.strptime(p[2], "%Y-%m-%d")
                        days = (exp - today).days
                        status = "Active" if days >= 0 else "Expired"
                    except: days, status = 0, "Unknown"
                    users.append({
                        "username": p[0], "password": p[1], "expiry": p[2],
                        "status": status, "days_left": max(0, days), "limit": p[3] if len(p)>3 else "1",
                        "type": "SSH/SSL"
                    })
    return jsonify(users)

@app.route('/api/users/create', methods=['POST'])
def create_user():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    d = request.json
    un = d.get('username')
    pw = d.get('password')
    exp_days = int(d.get('days', 30))
    limit = d.get('limit', '1')
    
    if run_command(f"id -u {un}") != "": return jsonify({"error": "Usuario ya existe"})
    
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=exp_days)).strftime('%Y-%m-%d')
    run_command(f"useradd -M -s /bin/false -e {exp_date} {un}")
    run_command(f"echo '{un}:{pw}' | chpasswd")
    
    if not os.path.exists(os.path.dirname(USERS_DB)): os.makedirs(os.path.dirname(USERS_DB))
    with open(USERS_DB, "a") as f: f.write(f"{un}:{pw}:{exp_date}:{limit}\n")
    return jsonify({"success": True})

@app.route('/api/users/delete', methods=['POST'])
def delete_user():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    un = request.json.get('username')
    run_command(f"userdel -f {un}")
    if os.path.exists(USERS_DB):
        lines = open(USERS_DB).readlines()
        with open(USERS_DB, 'w') as f:
            for l in lines:
                if not l.startswith(f"{un}:"): f.write(l)
    return jsonify({"success": True})

@app.route('/api/users/edit', methods=['POST'])
def edit_user():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    d = request.json
    un = d.get('username')
    pw = d.get('password')
    limit = d.get('limit')
    
    if pw: run_command(f"echo '{un}:{pw}' | chpasswd")
    
    if os.path.exists(USERS_DB):
        lines = open(USERS_DB).readlines()
        with open(USERS_DB, 'w') as f:
            for l in lines:
                if l.startswith(f"{un}:"):
                    p = l.strip().split(':')
                    db_pw = pw if pw else p[1]
                    db_exp = p[2]
                    db_lim = limit if limit else (p[3] if len(p)>3 else "1")
                    f.write(f"{un}:{db_pw}:{db_exp}:{db_lim}\n")
                else: f.write(l)
    return jsonify({"success": True})

@app.route('/api/users/renew', methods=['POST'])
def renew_user():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    un, days = request.json.get('username'), request.json.get('days')
    new_exp = ""
    if os.path.exists(USERS_DB):
        lines = open(USERS_DB).readlines()
        with open(USERS_DB, 'w') as f:
            for l in lines:
                if l.startswith(f"{un}:"):
                    p = l.strip().split(':')
                    cur_exp = datetime.datetime.strptime(p[2], "%Y-%m-%d")
                    new_e = cur_exp + datetime.timedelta(days=int(days))
                    new_exp = new_e.strftime("%Y-%m-%d")
                    f.write(f"{p[0]}:{p[1]}:{new_exp}:{p[3] if len(p)>3 else '1'}\n")
                else: f.write(l)
    if new_exp: run_command(f"chage -E {new_exp} {un}")
    return jsonify({"success": True, "new_expiry": new_exp})

@app.route('/api/users/toggle-lock', methods=['POST'])
def toggle_lock():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    un = request.json.get('username')
    st = run_command(f"passwd -S {un}")
    is_locked = " L " in st
    if is_locked: run_command(f"usermod -U {un}")
    else: run_command(f"usermod -L {un}")
    return jsonify({"success": True, "locked": not is_locked})

# ====== SERVICIOS ======

@app.route('/api/service/status')
def services_status():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    res = []
    for s in SERVICE_MAP:
        installed = is_installed(s["id"])
        active = is_service_active(s["id"]) if installed else False
        res.append({**s, "installed": installed, "active": active, "port": get_port_for_service(s["id"])})
    return jsonify(res)

@app.route('/api/service/action', methods=['POST'])
def service_action():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    sid, act = request.json.get('id'), request.json.get('action')
    if sid == 'ssh': sid = 'sshd'
    run_command(f"systemctl {act} {sid}")
    return jsonify({"success": True})

@app.route('/api/service/install/stunnel4/simple', methods=['POST'])
def install_stunnel4_simple():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    ctype = request.json.get('type', '1')
    port = request.json.get('port', '443')
    
    option = "1"
    if "Proxy" in ctype: option = "2"
    elif "Universal" in ctype or "Combinado" in ctype: option = "3"
    
    cmd = f'bash /etc/MaximusVpsMx/modules/install_stunnel_web.sh {option} {port}'
    result = run_install_command(cmd)
    
    if result != "TIMEOUT":
        run_command("systemctl enable --now stunnel4")
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Timeout"})

@app.route('/api/service/install/generic', methods=['POST'])
def install_generic():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    sid = request.json.get('id')
    port = request.json.get('port')
    
    scripts = {
        "mx-proxy": f"bash /etc/MaximusVpsMx/modules/install_mx-proxy.sh {port}",
        "hysteria": f"bash /etc/MaximusVpsMx/modules/install_hysteria.sh", # Se puede extender
        "udp-custom": f"bash /etc/MaximusVpsMx/modules/install_udp-custom.sh"
    }
    
    cmd = scripts.get(sid)
    if not cmd: return jsonify({"success": False, "error": "No instalador"})
    
    run_install_command(cmd)
    run_command(f"systemctl enable --now {sid}")
    return jsonify({"success": True})


@app.route('/api/service/proxy/port', methods=['POST'])
def port_proxy_python():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    port = request.json.get('port')
    if port and port.isdigit():
        run_command(f"bash /etc/MaximusVpsMx/modules/install_mx-proxy.sh {port}")
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid port"})

@app.route('/api/service/stunnel4/uninstall', methods=['POST'])
def uninstall_stunnel4():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    run_command("systemctl stop stunnel4; apt-get purge stunnel4 -y; rm -rf /etc/stunnel")
    return jsonify({"success": True})

@app.route('/api/service/port/update', methods=['POST'])
def update_service_port():
    if 'auth' not in session: return jsonify({"error": "Unauthorized"}), 401
    sid = request.json.get('id')
    port = request.json.get('port')
    
    if not sid or not port or not port.isdigit():
        return jsonify({"success": False, "error": "Datos inválidos"})
        
    if sid == "ssh" or sid == "sshd":
        run_command(f"sed -i 's/^#?Port .*/Port {port}/' /etc/ssh/sshd_config && systemctl restart ssh")
    elif sid == "dropbear":
        run_command(f"sed -i 's/DROPBEAR_PORT=.*/DROPBEAR_PORT={port}/' /etc/default/dropbear && systemctl restart dropbear")
    elif sid == "stunnel4" or sid == "stunnel":
        run_command(f"sed -i 's/accept = .*/accept = {port}/g' /etc/stunnel/stunnel.conf && systemctl restart stunnel4")
    elif sid == "mx-proxy":
        run_command(f"bash /etc/MaximusVpsMx/modules/install_mx-proxy.sh {port}")
    elif sid == "udp-custom" or sid == "hysteria":
        # Manejo de Rangos (ej: 7000:8000 o 7000-8000)
        port = port.replace('-', ':')
        internal_port = "36712" if sid == "udp-custom" else "36713"
        
        # 1. Obtener rango viejo para limpiar
        old_range = run_command(f"iptables -t nat -L PREROUTING -n | grep ':{internal_port}' | awk '{{print $7}}' | awk -F: '{{print $NF}}' | head -1")
        if old_range:
            run_command(f"iptables -t nat -D PREROUTING -p udp --dport {old_range} -j REDIRECT --to-port {internal_port}")
            run_command(f"ufw delete allow {old_range.replace(':', '/')}/udp")
        
        # 2. Aplicar nuevo rango
        run_command(f"iptables -t nat -I PREROUTING -p udp --dport {port} -j REDIRECT --to-port {internal_port}")
        run_command(f"ufw allow {port.replace(':', ':')}/udp")
        run_command("iptables-save > /etc/iptables/rules.v4")
        run_command(f"systemctl restart {sid}")
    else:
        return jsonify({"success": False, "error": "Servicio no soportado"})
        
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, threaded=True)
