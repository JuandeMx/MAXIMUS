from flask import Flask, request, jsonify, session, Response
import subprocess
import os
import datetime
import time
import json
import sqlite3

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

def is_service_active(name):
    # Algunos servicios no tienen .service tradicional
    if name == "ssh": name = "sshd"
    return subprocess.run(f"systemctl is-active --quiet {name}", shell=True).returncode == 0

def is_installed(name):
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
    }
    return ports.get(name, "--")

# --- CPU Telemetry ---
def get_cpu_info():
    try:
        with open('/proc/stat', 'r') as f:
            for line in f:
                if line.startswith('cpu '):
                    fields = [float(column) for column in line.strip().split()[1:]]
                    return fields[3], sum(fields)
    except: return 0, 0

_prev_idle, _prev_total = get_cpu_info()

def get_real_cpu_usage():
    global _prev_idle, _prev_total
    idle, total = get_cpu_info()
    idle_delta = idle - _prev_idle
    total_delta = total - _prev_total
    _prev_idle, _prev_total = idle, total
    if total_delta <= 0: return 0.0
    return round(100.0 * (1.0 - idle_delta / total_delta), 1)

def get_system_stats():
    mem = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split(':')
                if len(parts) == 2: mem[parts[0].strip()] = int(parts[1].split()[0])
        total = mem.get('MemTotal', 0) // 1024
        avail = mem.get('MemAvailable', mem.get('MemFree', 0)) // 1024
        used = total - avail
    except: total = used = avail = 0

    iface = run_command("ip route show | grep default | awk '{print $5}'") or "eth0"
    rx = tx = 0
    try:
        with open('/proc/net/dev', 'r') as f:
            for line in f:
                if iface in line:
                    parts = line.split()
                    rx = round(int(parts[1]) / 1073741824, 2)
                    tx = round(int(parts[9]) / 1073741824, 2)
    except: pass

    total_users = 0
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f: total_users = sum(1 for line in f if line.strip())

    # Disk Info Completa
    try:
        df_out = run_command("df -h / | awk 'NR==2 {print $2, $3, $5}'").split()
        d_total, d_used, d_perc = df_out[0], df_out[1], df_out[2].replace('%','')
    except: d_total, d_used, d_perc = "0", "0", "0"

    # Final Dictionary with absolute defaults for every field
    return {
        "ram": {"total": total or 1, "used": used or 0, "percent": round((used/total*100),1) if total > 0 else 0},
        "cpu": {"load": get_real_cpu_usage() or 0.0, "cores": os.cpu_count() or 1, "model": run_command("lscpu | grep 'Model name' | sed 's/.*: *//'") or "CPU Genérica"},
        "disk": {"total": d_total or "--", "used": d_used or "--", "percent": d_perc or "0"},
        "network": {"rx": rx or "0", "tx": tx or "0", "interface": iface or "eth0"},
        "uptime": run_command("uptime -p") or "calculando...",
        "load_avg": run_command("cat /proc/loadavg | awk '{print $1, $2, $3}'") or "--",
        "online": run_command("netstat -antp | grep ESTABLISHED | grep -v '127.0.0.1' | wc -l") or "0",
        "system": {
            "os": run_command("grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"'") or "Linux",
            "kernel": run_command("uname -r") or "--",
            "hostname": run_command("hostname") or "vps-server",
            "ip": run_command("curl -s ipv4.icanhazip.com") or "127.0.0.1"
        },
        "total_users": total_users,
        "ts": int(time.time())
    }

SERVICE_MAP = [
    {"id": "ssh", "name": "SSH", "icon": "fa-terminal", "desc": "Acceso Principal Secure Shell"},
    {"id": "dropbear", "name": "Dropbear", "icon": "fa-shield-halved", "desc": "SSH de bajo consumo"},
    {"id": "stunnel4", "name": "Stunnel4", "icon": "fa-lock", "desc": "Túnel SSL/TLS"},
    {"id": "ws-epro", "name": "WS-EPRO", "icon": "fa-globe", "desc": "WebSocket Proxy Python"},
    {"id": "mx-proxy", "name": "Python Proxy", "icon": "fa-code", "desc": "Proxy HTTP Custom"},
    {"id": "badvpn", "name": "BadVPN", "icon": "fa-satellite-dish", "desc": "UDP Gateway para Juegos"},
    {"id": "mx-slowdns", "name": "SlowDNS", "icon": "fa-tower-broadcast", "desc": "Túnel DNS over UDP"},
    {"id": "udp-custom", "name": "UDP Custom", "icon": "fa-bolt", "desc": "Protocolo UDP Optimizado"},
    {"id": "hysteria", "name": "Hysteria v2", "icon": "fa-rocket", "desc": "Protocolo QUIC de alta velocidad"},
    {"id": "x-ui", "name": "X-UI", "icon": "fa-table-columns", "desc": "Panel Gestión Xray/V2Ray"},
]

# ========== ROUTES ==========

@app.route('/')
def index():
    if 'logged_in' not in session: return app.send_static_file('login.html')
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
            try:
                data = get_system_stats()
                yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                # Si falla una lectura, enviamos un keep-alive para no cerrar la conexión
                yield f"data: {json.dumps({'error': str(e), 'ts': int(time.time())})}\n\n"
            time.sleep(2)
    return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/api/debug')
def debug_sys():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    return jsonify({
        "proc_meminfo": run_command("cat /proc/meminfo | head -5"),
        "proc_stat": run_command("cat /proc/stat | head -1"),
        "df": run_command("df -h /"),
        "ip": run_command("ip addr"),
        "python": run_command("python3 --version"),
        "time": datetime.datetime.now().isoformat()
    })

@app.route('/api/stats')
def stats():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    return jsonify(get_system_stats())

@app.route('/api/users/list')
def list_users():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
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
                        "status": status, "days_left": max(0, days), "limit": p[3] if len(p)>3 else "1"
                    })
    return jsonify(users)

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

@app.route('/api/tools/optimize', methods=['POST'])
def optimize_vps():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    cmd = "sync; echo 3 > /proc/sys/vm/drop_caches; journalctl --vacuum-time=1d; apt-get clean"
    r = run_command_full(cmd)
    return jsonify({"success": True, "log": [r['stdout'], r['stderr']]})

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

@app.route('/api/tools/traffic')
def tool_traffic():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    stats = get_system_stats()
    top_ips = []
    # Obtener Top IPs (opcional, básico)
    raw_ips = run_command("netstat -antu | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head -10")
    for line in raw_ips.split('\n'):
        p = line.strip().split()
        if len(p) == 2: top_ips.append({"ip": p[1], "connections": p[0]})
    
    return jsonify({
        "interface": stats['network']['interface'],
        "rx_gb": stats['network']['rx'],
        "tx_gb": stats['network']['tx'],
        "top_ips": top_ips
    })

@app.route('/api/service/status')
def services_status():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    res = []
    for s in SERVICE_MAP:
        installed = is_installed(s["id"])
        active = is_service_active(s["id"]) if installed else False
        res.append({**s, "installed": installed, "active": active, "port": get_port_for_service(s["id"])})
    return jsonify(res)

@app.route('/api/service/action', methods=['POST'])
def service_action():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    sid, act = request.json.get('id'), request.json.get('action')
    if sid == 'ssh': sid = 'sshd'
    run_command(f"systemctl {act} {sid}")
    return jsonify({"success": True})

@app.route('/api/tools/exec', methods=['POST'])
def terminal_exec():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    cmd = request.json.get('command', '')
    safe_prefixes = ['netstat', 'ss ', 'free ', 'df ', 'uptime', 'vnstat', 'whoami', 'id ', 'ls ', 'grep ', 'awk ']
    if not any(cmd.strip().startswith(p) for p in safe_prefixes):
        return jsonify({"error": "Comando no autorizado"}), 403
    return jsonify(run_command_full(cmd))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, threaded=True)
