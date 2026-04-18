#!/usr/bin/env python3
import os, time, datetime

# MaximusVpsMx Elite Auth Module v1.0
USER_DB = "/etc/MaximusVpsMx/users.db"

def get_user_info(target_user):
    if not os.path.exists(USER_DB):
        return None
    try:
        with open(USER_DB, "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 3 and parts[0] == target_user:
                    # user:pass:exp:hwid:limit
                    info = {
                        "user": parts[0],
                        "pass": parts[1],
                        "exp": parts[2],
                        "hwid": parts[3] if len(parts) > 3 else "OFF",
                        "limit": int(parts[4]) if len(parts) > 4 else 1
                    }
                    return info
    except:
        pass
    return None

def check_limit(username, limit):
    # Contamos procesos del usuario. 
    # Cada conexión SSH/Dropbear suele generar al menos 1-2 procesos del usuario.
    # Usamos pgrep para mayor precisión.
    try:
        cmd = f"pgrep -u {username} | wc -l"
        count = int(os.popen(cmd).read().strip())
        # Ajuste: A veces el sistema reporta 0 si el proceso es muy efímero.
        # En Maximus tomamos el límite como sesiones activas.
        if count >= limit:
            return False, f"Limit Reached ({count}/{limit})"
    except:
        pass
    return True, "OK"

def verify_hwid(username, sent_hwid, db_hwid):
    if db_hwid == "OFF":
        return True, "HUID Disabled"
    
    if db_hwid == "NONE":
        # Bloqueo Automático (Primera conexión)
        try:
            # Actualizar la DB con el nuevo HUID
            with open(USER_DB, "r") as f:
                lines = f.readlines()
            with open(USER_DB, "w") as f:
                for line in lines:
                    if line.startswith(f"{username}:"):
                        parts = line.strip().split(":")
                        parts[3] = sent_hwid
                        f.write(":".join(parts) + "\n")
                    else:
                        f.write(line)
            return True, "HUID Registered"
        except:
            return False, "DB Error"
            
    if sent_hwid == db_hwid:
        return True, "Match"
    else:
        return False, "HWID Mismatch"

def authenticate_elite(headers):
    # Extraer Usuario y HUID de los headers HTTP
    user = None
    huid = "NONE"
    
    for line in headers.split("\n"):
        if "X-User:" in line:
            user = line.split("X-User:")[1].strip()
        if "X-HUID:" in line:
            huid = line.split("X-HUID:")[1].strip()
            
    if not user:
        # Si no hay usuario en los headers, permitimos pasar (Auth interna de SSH)
        # pero no aplicamos HUID ni Límites.
        return True, "No Headers"

    info = get_user_info(user)
    if not info:
        return False, "User not in Database"

    # 1. Verificar Expiración
    try:
        exp_date = datetime.datetime.strptime(info["exp"], "%Y-%m-%d")
        if datetime.datetime.now() > exp_date:
            return False, "Account Expired"
    except:
        pass

    # 2. Verificar Límites
    ok, msg = check_limit(user, info["limit"])
    if not ok:
        return False, msg

    # 3. Verificar HWID
    ok, msg = verify_hwid(user, huid, info["hwid"])
    if not ok:
        return False, msg

    return True, "Elite Validated"
