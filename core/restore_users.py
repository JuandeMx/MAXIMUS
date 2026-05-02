#!/bin/bash

# Maximus Restoration Master v3.0 (Official Format Edition)
# Este script usa el formato EXACTO del panel MX

DB_PATH="/etc/MaximusVpsMx/maximus.db"
DB_PATH2="/etc/MaximusVpsMx/users.db"
DB_PATH3="/etc/MaximusVpsMx/hysteria_users.db"

echo -e "🚀 Sincronizando 45 usuarios con el formato OFICIAL del panel..."

# Asegurar directorio
mkdir -p /etc/MaximusVpsMx/

# 1. Limpiar y Crear usando el comando oficial del panel
setup_db() {
    local path=$1
    rm -f "$path"
    # Formato oficial detectado en el script MX
    sqlite3 "$path" "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, expiry_date TEXT, hwid TEXT DEFAULT 'OFF', device_limit INTEGER DEFAULT 1);"
}

setup_db "$DB_PATH"
setup_db "$DB_PATH2"
setup_db "$DB_PATH3"

# 2. Lista de 45 usuarios
USERS=(
    "Juande|mx|2026-05-15" "Hugo|123|2026-05-24" "Juan|123|2026-05-24" "Andrea|1234|2026-05-25"
    "Oscar|Paciencia|2026-05-25" "Mario|Cliente|2026-05-26" "myreyna|bella|2026-05-26" "Ariel|Byjuande|2026-05-27"
    "prueba|p1|2026-05-10" "Prueba1|Pruebacliente|2026-05-05" "Clientemartes|Martes|2026-05-28" "Rooh|Rooh1|2026-05-28"
    "Sergio|Cliente1|2026-05-28" "Cliente-hija|Hija10|2026-05-28" "Pepito|Buchaina|2026-05-05" "Alberto|Alberto1|2026-05-29"
    "Juaquin|Juaquin1|2026-05-29" "Juaquin2|Juaquin2|2026-05-29" "Marcelo|Marcelo|2026-05-29" "Tiziano|Tiziano|2026-05-29"
    "Armando|Armando|2026-05-29" "Marcela|Marcela|2026-05-29" "Lauturo|Lautaru|2026-05-29" "Alfredo|Alfredo|2026-05-29"
    "Gogy2|Gogy2|2026-05-29" "Pedro|Pedrogay|2026-05-30" "Rodrigo|ElAmerica|2026-05-30" "Noconecta|Tuhermana|2026-05-30"
    "Luciana|Arg|2026-05-30" "Federico|Cliente100|2026-05-30" "Alex|Alexcito|2026-05-30" "Jhona|Tortilla|2026-05-30"
    "Luka|Tvsmart|2026-05-30" "Fernanda|Yaestoyhastalamadre|2026-05-30" "Facu|Tomates|2026-05-28" "Xiomara|Claropersonal|2026-05-30"
    "MIAMORSOTE_BELLA_CHULA_PRECIOSA|TUFUTUROESPOSOBEBE|2026-05-31" "Luis|Luisitocomunica|2026-05-31" "Abel|Abel|2026-05-31"
    "Pruebass|Jsjs|2026-05-08" "Mihermano|Carlos|2026-05-31" "JULIETA|Tamarindo|2026-05-31" "Prueba1dia|Mex|2026-05-08"
    "Brian|Cliente|2026-05-31" "Yoel|Personal|2026-06-01"
)

# 3. Inyección usando el comando INSERT oficial
for row in "${USERS[@]}"; do
    IFS='|' read -r u p e <<< "$row"
    
    # Sistema
    if ! id "$u" &>/dev/null; then
        useradd -M -s /bin/false "$u" &>/dev/null
    fi
    echo "$u:$p" | chpasswd &>/dev/null
    
    # Insertar (usando comillas simples para evitar errores de shell)
    sqlite3 "$DB_PATH" "INSERT INTO users (username, password, expiry_date, hwid, device_limit) VALUES ('$u', '$p', '$e', 'OFF', 1);"
    sqlite3 "$DB_PATH2" "INSERT INTO users (username, password, expiry_date, hwid, device_limit) VALUES ('$u', '$p', '$e', 'OFF', 1);"
    sqlite3 "$DB_PATH3" "INSERT INTO users (username, password, expiry_date, hwid, device_limit) VALUES ('$u', '$p', '$e', 'OFF', 1);"
    
    echo -ne " [+] Sincronizando: $u\r"
done

echo -e "\n\n✅ ¡LISTO! Todos los clientes han sido restaurados con el formato oficial."
