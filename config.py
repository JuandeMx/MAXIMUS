import json
import os

CONFIG_FILE = "/etc/MaximusVpsMx/bot_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

# Cargar datos dinámicos
_cfg = load_config()

BOT_TOKEN = _cfg.get("BOT_TOKEN", "PENDIENTE")
ADMIN_ID = _cfg.get("ADMIN_ID", 0)
HOST_DOMAIN = _cfg.get("HOST_DOMAIN", "")
BOT_COMMAND = _cfg.get("BOT_COMMAND", "vip")


# Precios en Telegram Stars (XTR)
PRICE_7_DAYS = 50
PRICE_30_DAYS = 150

# Configuración Estática de Puertos
SSH_PORTS = "443, 80"
DROPBEAR_PORT = "44"
UDP_RANGE = "7100-7200"
UDP_SERVER_PORT = "7100" # Puerto principal UDP Custom
HYSTERIA_RANGE = "2000-5000"
HY_PORT = "2000" # Puerto principal Hysteria v2
HY_OBFS = "salamander"
HY_SNI = "bing.com"

WELCOME_MSG = """
🤖 *Bienvenido al Bot de Gestión Maximus Elite* 🛡️

Soy tu asistente para la creación de cuentas SSH/VPN Premium y Trial.

*Selecciona una opción:*
"""
