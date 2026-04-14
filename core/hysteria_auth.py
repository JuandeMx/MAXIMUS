import sys
import json
import datetime
import os

# Ruta de la base de datos de usuarios
DB_PATH = "/etc/MaximusVpsMx/hysteria_users.db"

def log_debug(msg):
    with open("/var/log/MaximusVpsMx/hysteria_auth_debug.log", "a") as f:
        f.write(f"[{datetime.datetime.now()}] {msg}\n")

def check_auth():
    try:
        # Hysteria manda el JSON por stdin
        line = sys.stdin.readline()
        if not line:
            return
        
        data = json.loads(line)
        client_auth = data.get("auth", "")
        
        if not os.path.exists(DB_PATH):
            print(json.dumps({"ok": False, "msg": "No DB found"}))
            return

        with open(DB_PATH, "r") as f:
            for line in f:
                # Formato: user:pass:expiry:up_mbps:down_mbps
                parts = line.strip().split(":")
                if len(parts) < 5:
                    continue
                
                user, password, expiry_str, up_m, down_m = parts
                
                if password == client_auth:
                    # Verificar expiración
                    expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
                    if datetime.datetime.now() <= expiry_date:
                        # Convertir Mbps a bps (bits por segundo)
                        # 1 Mbps = 1,000,000 bps
                        up_bps = int(up_m) * 1000000
                        down_bps = int(down_m) * 1000000
                        
                        resp = {
                            "ok": True,
                            "id": user,
                            "up": up_bps,
                            "down": down_bps
                        }
                        print(json.dumps(resp))
                        return
                    else:
                        print(json.dumps({"ok": False, "msg": "Account expired"}))
                        return

        # Si llega aquí, no se encontró el usuario/clave
        print(json.dumps({"ok": False, "msg": "Invalid credentials"}))

    except Exception as e:
        log_debug(f"Error: {str(e)}")
        print(json.dumps({"ok": False, "msg": "Internal server error"}))

if __name__ == "__main__":
    check_auth()
