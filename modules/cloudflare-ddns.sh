#!/bin/bash
# MaximusVpsMx - Cloudflare Dynamic DNS Updater (Multi-Subdominio)
# Comprueba la IP pública cada 5 min y actualiza TODOS los registros A en Cloudflare

CONFIG_FILE="/etc/MaximusVpsMx/cloudflare.conf"
LOG_FILE="/var/log/MaximusVpsMx/cloudflare-ddns.log"

# Cargar configuración
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[$(date)] ERROR: No existe $CONFIG_FILE" >> "$LOG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

if [ -z "$CF_API_TOKEN" ] || [ -z "$CF_ZONE_ID" ]; then
    echo "[$(date)] ERROR: Faltan datos en $CONFIG_FILE" >> "$LOG_FILE"
    exit 1
fi

# Obtener IP pública actual
IP_ACTUAL=$(curl -s https://api.ipify.org)
[ -z "$IP_ACTUAL" ] && IP_ACTUAL=$(curl -s https://ipv4.icanhazip.com)
[ -z "$IP_ACTUAL" ] && { echo "[$(date)] ERROR: No se pudo obtener IP pública." >> "$LOG_FILE"; exit 1; }

# Leer la IP anterior guardada localmente
IP_FILE="/etc/MaximusVpsMx/.last_ip"
IP_ANTERIOR=""
[ -f "$IP_FILE" ] && IP_ANTERIOR=$(cat "$IP_FILE")

# Si la IP no cambió, salir silenciosamente
if [ "$IP_ACTUAL" == "$IP_ANTERIOR" ]; then
    exit 0
fi

echo "[$(date)] ¡IP CAMBIÓ! $IP_ANTERIOR → $IP_ACTUAL" >> "$LOG_FILE"

# Obtener TODOS los registros tipo A de la zona
ALL_RECORDS=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records?type=A&per_page=100" \
    -H "Authorization: Bearer $CF_API_TOKEN" \
    -H "Content-Type: application/json")

SUCCESS=$(echo "$ALL_RECORDS" | jq -r '.success')
if [ "$SUCCESS" != "true" ]; then
    echo "[$(date)] ERROR: Cloudflare API falló: $ALL_RECORDS" >> "$LOG_FILE"
    exit 1
fi

# Contar cuántos registros A hay
TOTAL=$(echo "$ALL_RECORDS" | jq '.result | length')
UPDATED=0

# Recorrer CADA registro A y actualizar los que tengan la IP vieja (o primera vez)
for i in $(seq 0 $(($TOTAL - 1))); do
    RECORD_ID=$(echo "$ALL_RECORDS" | jq -r ".result[$i].id")
    RECORD_NAME=$(echo "$ALL_RECORDS" | jq -r ".result[$i].name")
    RECORD_IP=$(echo "$ALL_RECORDS" | jq -r ".result[$i].content")
    RECORD_PROXIED=$(echo "$ALL_RECORDS" | jq -r ".result[$i].proxied")

    # Solo actualizar si la IP del registro coincide con la IP anterior (o si es primera vez)
    if [ "$RECORD_IP" == "$IP_ANTERIOR" ] || [ -z "$IP_ANTERIOR" ]; then
        UPDATE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records/$RECORD_ID" \
            -H "Authorization: Bearer $CF_API_TOKEN" \
            -H "Content-Type: application/json" \
            --data "{\"type\":\"A\",\"name\":\"$RECORD_NAME\",\"content\":\"$IP_ACTUAL\",\"ttl\":120,\"proxied\":$RECORD_PROXIED}")

        UPD_OK=$(echo "$UPDATE" | jq -r '.success')
        if [ "$UPD_OK" == "true" ]; then
            echo "[$(date)] ✅ $RECORD_NAME → $IP_ACTUAL" >> "$LOG_FILE"
            UPDATED=$(($UPDATED + 1))
        else
            echo "[$(date)] ❌ Error en $RECORD_NAME: $UPDATE" >> "$LOG_FILE"
        fi
    fi
done

# Guardar la IP actual como referencia
echo "$IP_ACTUAL" > "$IP_FILE"

echo "[$(date)] Resumen: $UPDATED de $TOTAL registros actualizados." >> "$LOG_FILE"
