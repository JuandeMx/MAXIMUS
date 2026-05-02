import subprocess
import os
import datetime
import tarfile
import shutil

BACKUP_DIR = "/etc/MaximusVpsMx/backups"
USER_DB = "/etc/MaximusVpsMx/users.db"
MAXIMUS_DB = "/etc/MaximusVpsMx/maximus.db"
HYSTERIA_DB = "/etc/MaximusVpsMx/hysteria_users.db"
BOT_CONFIG = "/etc/MaximusVpsMx/bot_config.json"
CF_CONFIG = "/etc/MaximusVpsMx/cloudflare.conf"

def _run(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except:
        return None

def ensure_backup_dir():
    """Crea el directorio de backups y lo protege contra borrado desde el panel."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    # Proteger el directorio (solo root con chattr -i puede borrar)
    _run(f"chattr +i {BACKUP_DIR}")

def create_backup(label=None):
    """Crea un backup completo con timestamp. Retorna (True, filename) o (False, error)."""
    ensure_backup_dir()
    
    now = datetime.datetime.now()
    if label:
        name = f"backup_{label}_{now.strftime('%Y%m%d_%H%M%S')}.tar.gz"
    else:
        name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}.tar.gz"
    
    filepath = os.path.join(BACKUP_DIR, name)
    
    # Temporalmente quitar protección para escribir
    _run(f"chattr -i {BACKUP_DIR}")
    
    try:
        with tarfile.open(filepath, "w:gz") as tar:
            for f in [USER_DB, MAXIMUS_DB, HYSTERIA_DB, BOT_CONFIG, CF_CONFIG,
                       "/etc/passwd", "/etc/shadow"]:
                if os.path.exists(f):
                    tar.add(f)
        
        size = os.path.getsize(filepath)
        size_kb = round(size / 1024, 1)
        
        # Re-proteger
        _run(f"chattr +i {BACKUP_DIR}")
        
        return True, name, size_kb
    except Exception as e:
        _run(f"chattr +i {BACKUP_DIR}")
        return False, str(e), 0

def list_backups():
    """Lista todos los backups disponibles. Retorna lista de dicts."""
    ensure_backup_dir()
    backups = []
    
    _run(f"chattr -i {BACKUP_DIR}")
    
    try:
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.endswith(".tar.gz"):
                path = os.path.join(BACKUP_DIR, f)
                size = round(os.path.getsize(path) / 1024, 1)
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
                backups.append({
                    "filename": f,
                    "size_kb": size,
                    "date": mtime.strftime("%Y-%m-%d %H:%M")
                })
    except:
        pass
    
    _run(f"chattr +i {BACKUP_DIR}")
    return backups

def delete_backup(filename):
    """Elimina un backup específico (solo desde el bot)."""
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return False, "Archivo no encontrado"
    
    _run(f"chattr -i {BACKUP_DIR}")
    try:
        os.remove(filepath)
        _run(f"chattr +i {BACKUP_DIR}")
        return True, "Eliminado"
    except Exception as e:
        _run(f"chattr +i {BACKUP_DIR}")
        return False, str(e)

def restore_backup(filename):
    """Restaura un backup específico. Retorna (True, msg) o (False, error)."""
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return False, "Archivo no encontrado"
    
    _run(f"chattr -i {BACKUP_DIR}")
    
    try:
        with tarfile.open(filepath, "r:gz") as tar:
            tar.extractall("/")
        
        _run(f"chattr +i {BACKUP_DIR}")
        return True, "Backup restaurado exitosamente"
    except Exception as e:
        _run(f"chattr +i {BACKUP_DIR}")
        return False, str(e)

def setup_daily_cron():
    """Configura el cron para backup automático diario a las 3 AM."""
    cron_cmd = "0 3 * * * /usr/bin/python3 -c \"import sys; sys.path.insert(0,'/etc/MaximusVpsMx'); from core.backup_manager import create_backup; create_backup('auto')\" >/dev/null 2>&1"
    
    # Verificar si ya existe
    existing = _run("crontab -l 2>/dev/null") or ""
    if "backup_manager" in existing or "create_backup" in existing:
        return  # Ya configurado
    
    # Agregar al crontab
    new_cron = existing + "\n" + cron_cmd + "\n"
    _run(f"echo '{new_cron}' | crontab -")
