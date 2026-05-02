#!/bin/bash

# Maximus Restoration Master v2.0 (Bash Edition)
# Diseñado para una limpieza profunda y restauración de 45 usuarios

DB_PATH="/etc/MaximusVpsMx/maximus.db"
DB_PATH2="/etc/MaximusVpsMx/users.db"
DB_PATH3="/etc/MaximusVpsMx/hysteria_users.db"

echo -e "🚀 Iniciando LIMPIEZA MAESTRA y Restauración de 45 clientes..."

# 1. Borrar bases de datos corruptas
rm -f "$DB_PATH" "$DB_PATH2" "$DB_PATH3"

# 2. Crear las bases de datos desde cero con el formato exacto
create_db() {
    local path=$1
    sqlite3 "$path" "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, expiry_date TEXT, hwid TEXT DEFAULT 'OFF', device_limit INTEGER DEFAULT 1);"
}

# Asegurar directorio
mkdir -p /etc/MaximusVpsMx/

create_db "$DB_PATH"
create_db "$DB_PATH2"
create_db "$DB_PATH3"

# 3. Lista de usuarios (45 en total)
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

# 4. Inyección Masiva
for row in "${USERS[@]}"; do
    IFS='|' read -r u p e <<< "$row"
    
    # Crear en Linux (Solo si no existe)
    if ! id "$u" &>/dev/null; then
        useradd -M -s /bin/false "$u" &>/dev/null
    fi
    echo "$u:$p" | chpasswd &>/dev/null
    
    # Inyectar en las 3 bases de datos
    sqlite3 "$DB_PATH" "INSERT INTO users (username, password, expiry_date, hwid, device_limit) VALUES ('$u', '$p', '$e', 'OFF', 1);"
    sqlite3 "$DB_PATH2" "INSERT INTO users (username, password, expiry_date, hwid, device_limit) VALUES ('$u', '$p', '$e', 'OFF', 1);"
    sqlite3 "$DB_PATH3" "INSERT INTO users (username, password, expiry_date, hwid, device_limit) VALUES ('$u', '$p', '$e', 'OFF', 1);"
    
    echo -e " [+] Restaurado: $u"
done

echo -e "\n✅ ¡PROCESO COMPLETADO! 45 clientes listos en el panel."
