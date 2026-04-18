from flask import Flask, request, jsonify, session
import subprocess
import os
import datetime
import time

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
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return ""

def get_system_stats():
    # RAM
    ram_total = run_command("free -m | awk 'NR==2 {print $2}'")
    ram_used = run_command("free -m | awk 'NR==2 {print $3}'")
    
    # CPU Load
    cpu_load = run_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
    
    # Disco
    disk_total = run_command("df -h / | awk 'NR==2 {print $2}'")
    disk_used = run_command("df -h / | awk 'NR==2 {print $3}'")
    disk_perc = run_command("df -h / | awk 'NR==2 {print $5}'")
    
    # Uptime
    uptime = run_command("uptime -p")
    
    # Usuarios Online (SSH/ESTABLISHED)
    online = run_command("netstat -antp | grep -E 'sshd|dropbear' | grep ESTABLISHED | wc -l")
    
    return {
        "ram": {"total": ram_total, "used": ram_used},
        "cpu": cpu_load,
        "disk": {"total": disk_total, "used": disk_used, "percent": disk_perc},
        "uptime": uptime,
        "online": online
    }

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

@app.route('/api/stats')
def stats():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    return jsonify(get_system_stats())

@app.route('/api/users/list')
def list_users():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    users = []
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r") as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) >= 3:
                     users.append({
                         "username": parts[0],
                         "expiry": parts[2],
                         "type": "SSH/SSL",
                         "status": "Active" # Simplificado
                     })
    return jsonify(users)

@app.route('/api/create/ssh', methods=['POST'])
def create_ssh():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    days = 3
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=int(days))).strftime("%Y-%m-%d")
    
    run_command("rm -f /etc/passwd.lock /etc/shadow.lock")
    run_command(f"useradd -e {exp_date} -s /bin/false -M {username}")
    run_command(f"echo '{username}:{password}' | chpasswd")
    
    with open(USERS_DB, "a") as db:
        db.write(f"{username}:{password}:{exp_date}\n")
    
    return jsonify({"message": "Usuario creado", "expiry": exp_date})

@app.route('/api/service/status')
def services_status():
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
    
    services = [
        {"name": "SSH", "active": subprocess.run("systemctl is-active ssh", shell=True).returncode == 0},
        {"name": "Dropbear", "active": subprocess.run("systemctl is-active dropbear", shell=True).returncode == 0},
        {"name": "Python Proxy", "active": subprocess.run("systemctl is-active mx-proxy", shell=True).returncode == 0},
        {"name": "Stunnel4", "active": subprocess.run("systemctl is-active stunnel4", shell=True).returncode == 0},
        {"name": "Hysteria v2", "active": subprocess.run("systemctl is-active hysteria", shell=True).returncode == 0},
        {"name": "X-UI", "active": subprocess.run("systemctl is-active x-ui", shell=True).returncode == 0},
    ]
    return jsonify(services)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082)
