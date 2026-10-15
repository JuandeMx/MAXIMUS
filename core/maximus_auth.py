import os, time, datetime, psutil

# MaximusVpsMx Elite Auth Module v2.0 (High Performance)
USER_DB = "/etc/MaximusVpsMx/users.db"

# Caché simple en memoria para evitar I/O de disco excesivo
_user_cache = {}
_cache_ttl = 5 # segundos
_last_cache_update = 0

def get_user_info(target_user):
    global _last_cache_update, _user_cache
    
    current_time = time.time()
    if current_time - _last_cache_update > _cache_ttl:
        if os.path.exists(USER_DB):
            try:
                new_cache = {}
                with open(USER_DB, "r") as f:
                    for line in f:
                        parts = line.strip().split(":")
                        if len(parts) >= 3:
                            new_cache[parts[0]] = {
                                "user": parts[0],
                                "pass": parts[1],
                                "exp": parts[2],
                                "hwid": parts[3] if len(parts) > 3 else "OFF",
                                "limit": int(parts[4]) if len(parts) > 4 else 1,
                                "alias": parts[5] if len(parts) > 5 else parts[0]
                            }
                _user_cache = new_cache
                _last_cache_update = current_time
            except: pass
            
    return _user_cache.get(target_user)

def get_user_by_hwid(target_hwid):
    global _last_cache_update, _user_cache
    # Forzamos actualización de caché si está vieja llamando a get_user_info con un dummy
    get_user_info("dummy_trigger")
    clean_target = str(target_hwid).strip().lower()
    for username, info in _user_cache.items():
        hwid_clean = str(info.get("hwid", "")).strip().lower()
        user_clean = str(info.get("user", "")).strip().lower()
        if (hwid_clean == clean_target or user_clean == clean_target) and info.get("pass") == "HWID_INV":
            return info
    return None

def check_limit(username, limit):
    # Contamos procesos del usuario de forma eficiente usando psutil
    try:
        count = 0
        for proc in psutil.process_iter(['username']):
            try:
                if proc.info['username'] == username:
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if count >= limit:
            return False, f"Limit Reached ({count}/{limit})"
    except:
        pass
    return True, "OK"

def verify_hwid(username, sent_hwid, db_hwid):
    if db_hwid == "OFF":
        return True, "HUID Disabled"
    
    clean_sent = str(sent_hwid).strip().lower()
    clean_db = str(db_hwid).strip().lower()

    if clean_db in ["none", ""]:
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
            
    if clean_sent == clean_db:
        return True, "Match"
    else:
        return False, "HWID Mismatch"

def authenticate_elite(headers):
    # Extraer Usuario y HUID de los headers HTTP de forma flexible e insensible a mayúsculas
    user = None
    huid = "NONE"
    
    for raw_line in headers.split("\n"):
        line_str = raw_line.strip()
        if not line_str or ":" not in line_str:
            continue
        h_name, h_val = line_str.split(":", 1)
        h_name = h_name.strip().lower()
        h_val = h_val.strip()

        if h_name in ["x-user", "user"]:
            user = h_val
        elif h_name in ["x-huid", "x-hwid", "huid", "hwid", "x-device-id", "device-id"]:
            huid = h_val
            
    if not user:
        # Si no hay usuario en los headers, permitimos pasar (Auth interna de SSH)
        # pero no aplicamos HUID ni Límites.
        return True, "No Headers"

    # Si el cliente usa el usuario universal invisible mxhwid
    is_invisible = False
    if user.lower() == "mxhwid":
        info = get_user_by_hwid(huid)
        is_invisible = True
    else:
        info = get_user_info(user)
        # Fallback: si el usuario envió su HWID como username
        if not info:
            info = get_user_by_hwid(user)
            if info:
                is_invisible = True
        
    if not info:
        return False, "User not in Database"

    # 1. Verificar Expiración con parche de Zona Horaria (23:59:59)
    try:
        exp_date = datetime.datetime.strptime(info["exp"] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        if datetime.datetime.now() > exp_date:
            return False, "Account Expired"
    except:
        pass

    # 2. Verificar Límites (Los usuarios invisibles ya están limitados a 1 dispositivo por su HWID físico)
    if not is_invisible:
        ok, msg = check_limit(user, info["limit"])
        if not ok:
            return False, msg

    # 3. Verificar HWID
    ok, msg = verify_hwid(user, huid, info["hwid"])
    if not ok:
        return False, msg

    return True, "Elite Validated"
