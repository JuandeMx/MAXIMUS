from flask import Flask, request, jsonify
import subprocess
import os
import datetime

# Configuración de Frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('index.html')

# Configuración de Rutas
USERS_DB = "/etc/MaximusVpsMx/users.db"
HYSTERIA_DB = "/etc/MaximusVpsMx/hysteria_users.db"

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

@app.route('/api/create/ssh', methods=['POST'])
def create_ssh():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    # Force 3 days for web-created accounts
    days = 3

    if not username or not password:
        return jsonify({"error": "Faltan datos"}), 400

    exp_date = (datetime.datetime.now() + datetime.timedelta(days=int(days))).strftime("%Y-%m-%d")
    
    # Limpiar posibles locks de sistema
    run_command("rm -f /etc/passwd.lock /etc/shadow.lock")
    
    # 1. Verificar si el usuario ya existe en el sistema
    stdout_check, _, _ = run_command(f"id {username}")
    if stdout_check:
        return jsonify({"error": f"El usuario '{username}' ya existe en el servidor."}), 400

    # 2. Crear usuario en el sistema
    cmd_user = f"useradd -e {exp_date} -s /bin/false -M {username}"
    stdout, stderr, code = run_command(cmd_user)
    
    if code != 0:
        return jsonify({"error": "No se pudo crear el usuario", "details": stderr}), 400
    
    # Configurar password
    run_command(f"echo '{username}:{password}' | chpasswd")
    
    # Registrar en base de datos de Maximus
    with open(USERS_DB, "a") as db:
        db.write(f"{username}:{password}:{exp_date}\n")
    
    # Obtener IP del servidor
    server_ip, _, _ = run_command("wget -qO- ipv4.icanhazip.com")

    return jsonify({
        "message": "Usuario SSH creado correctamente",
        "username": username,
        "password": password,
        "expiry": exp_date,
        "server_ip": server_ip
    })

@app.route('/api/create/hysteria', methods=['POST'])
def create_hysteria():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    # Force 3 days for web-created accounts
    days = 3
    sni = data.get('sni', 'bing.com')
    limit_up = data.get('limit_up', 100)
    limit_down = data.get('limit_down', 100)

    if not username or not password:
        return jsonify({"error": "Faltan datos"}), 400

    exp_date = (datetime.datetime.now() + datetime.timedelta(days=int(days))).strftime("%Y-%m-%d")
    
    # Registrar en base de datos de Hysteria
    # Formato: user:pass:expiry:up_m:down_m
    with open(HYSTERIA_DB, "a") as db:
        db.write(f"{username}:{password}:{exp_date}:{limit_up}:{limit_down}\n")
    
    # Obtener IP del servidor
    server_ip, _, _ = run_command("wget -qO- ipv4.icanhazip.com")
    
    # Obtener puerto de Hysteria: Usaremos Port-Hopping
    hy_port = "2000-5000"
    
    # Obtener contraseña obfs de la configuración
    obfs_password = "maximus_obfs_maestra" # Valor por defecto
    
    return jsonify({
        "message": "Usuario Hysteria creado correctamente",
        "username": username,
        "password": password,
        "expiry": exp_date,
        "server_ip": server_ip,
        "link": f"hy2://{password}@{server_ip}:{hy_port}?insecure=1&sni={sni}&obfs=salamander&obfs-password={obfs_password}#({username})"
    })

if __name__ == '__main__':
    # El servidor corre internamente, se recomienda usar Gunicorn o similar en producción
    app.run(host='0.0.0.0', port=8082)
