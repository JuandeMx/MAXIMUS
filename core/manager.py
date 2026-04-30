import subprocess
import datetime
import random
import string

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip()
    except:
        return None

def check_user_exists(username):
    # Verifica en /etc/passwd si el usuario ya existe (usando el código de salida)
    try:
        result = subprocess.run(f"grep -q '^{username}:' /etc/passwd", shell=True)
        return result.returncode == 0
    except:
        return False

def create_ssh_user(username, password, days=3, limit=1):
    # Generar fecha de expiración para useradd (YYYY-MM-DD)
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    db_path = "/etc/MaximusVpsMx/users.db"
    
    cmd = f"useradd -M -s /bin/false -e {exp_date} {username}"
    if run_command(cmd) is None:
        return False, "Error al ejecutar useradd"
    
    # establecer contraseña
    if run_command(f"echo '{username}:{password}' | chpasswd") is None:
        return False, "Error al establecer contraseña"
    
    # Sincronizar con la base de datos de MX
    # Formato: user:pass:exp:hwid:limit
    user_entry = f"{username}:{password}:{exp_date}:OFF:{limit}"
    run_command(f"echo '{user_entry}' >> {db_path}")
    
    # Sincronizar con la base de datos de Hysteria v2
    # Formato: user:pass:exp:up:down (Ej: user:pass:2026-04-20:100:100)
    hy_db = "/etc/MaximusVpsMx/hysteria_users.db"
    hy_entry = f"{username}:{password}:{exp_date}:100:100"
    run_command(f"echo '{hy_entry}' >> {hy_db}")
    
    return True, exp_date

def extend_user_expiry(username, days=1):
    import datetime
    new_expiry = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    
    # 1. Actualizar Linux
    run_command(f"chage -E {new_expiry} {username}")
    
    # 2. Actualizar database.db de MX (archivo de texto)
    db_path = "/etc/MaximusVpsMx/users.db"
    run_command(f"sed -i 's/^\\({username}:[^:]*:\\)[^:]*/\\1{new_expiry}/' {db_path} 2>/dev/null || true")
    
    # 3. Actualizar Hysteria DB
    hy_db = "/etc/MaximusVpsMx/hysteria_users.db"
    run_command(f"sed -i 's/^\\({username}:[^:]*:\\)[^:]*/\\1{new_expiry}/' {hy_db} 2>/dev/null || true")
    
    return new_expiry

def remove_user(username):
    run_command(f"userdel -f {username} 2>/dev/null")
    run_command(f"sed -i '/^{username}:/d' /etc/MaximusVpsMx/users.db 2>/dev/null")
    run_command(f"sed -i '/^{username}:/d' /etc/MaximusVpsMx/hysteria_users.db 2>/dev/null")
    return True

def get_all_users():
    db_path = "/etc/MaximusVpsMx/users.db"
    lines = run_command(f"cat {db_path} 2>/dev/null")
    users = []
    if lines:
        for line in lines.splitlines():
            parts = line.strip().split(':')
            if len(parts) >= 3:
                users.append({'username': parts[0], 'expiry': parts[2]})
    return users

def generate_random_user(length=5):
    prefix = "trial"
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}_{random_str}"

def generate_random_pass(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_server_ip():
    # Detectar IP pública
    ip = run_command("curl -s ipv4.icanhazip.com")
    return ip if ip else "TU_IP_AQUI"

def get_hysteria_port():
    # Lee el puerto configurado en Hysteria
    port = run_command("grep 'listen:' /etc/hysteria/config.yaml 2>/dev/null | grep -o '[0-9]*' | head -1")
    return port if port else "443"

def get_hysteria_obfs():
    # Lee la contraseña obfs maestra
    obfs = run_command("grep 'password:' /etc/hysteria/config.yaml 2>/dev/null | tail -1 | awk '{print $NF}'")
    return obfs if obfs else "salamander"
