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
    # Verifica en /etc/passwd si el usuario ya existe
    res = run_command(f"grep -q '^{username}:' /etc/passwd")
    return res is not None

def create_ssh_user(username, password, days=3, limit=1):
    # Generar fecha de expiración para useradd (YYYY-MM-DD)
    exp_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    db_path = "/etc/MaximusVpsMx/users.db"
    
    # comando useradd: -M (no home), -s /bin/false (no shell), -e (expiry)
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
    
    return True, exp_date

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
