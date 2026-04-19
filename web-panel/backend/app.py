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
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except: return ""

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
    if d.get('user') == ADMIN_USER and d.get('pass') == ADMIN_PASS:
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, threaded=True)
