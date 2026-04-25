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
                                "limit": int(parts[4]) if len(parts) > 4 else 1
                            }
                _user_cache = new_cache
                _last_cache_update = current_time
            except: pass
            
    return _user_cache.get(target_user)

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
