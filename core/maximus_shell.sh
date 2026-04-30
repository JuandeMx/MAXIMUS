#!/bin/bash
# Maximus Dynamic Shell

username=$(whoami)
exp_date=$(grep "^${username}:" /etc/MaximusVpsMx/users.db 2>/dev/null | cut -d: -f3 2>/dev/null)

echo ""
echo -e "🛡️ USUARIO $username 🛡️"
echo ""
echo -e "⚡ DETALLES DE SU SERVIDOR ⚡"
echo ""

if [ -n "$exp_date" ]; then
    today=$(date +%s)
    exp=$(date -d "$exp_date" +%s)
    days_left=$(( (exp - today) / 86400 ))
    
    # Formatear la fecha a 'May 02, 2026'
    formatted_date=$(date -d "$exp_date" "+%b %d, %Y")
    
    echo -e "· VALIDO HASTA : $formatted_date 📅"
    echo -e "· TIENE $days_left DIAS RESTANTES"
else
    echo -e "· VALIDO HASTA : Ilimitado 📅"
    echo -e "· TIENE Ilimitados DIAS RESTANTES"
fi

echo ""
echo -e "✨ CUOTA ILIMITADA ♾️"
echo ""

# Mantener el canal SSH abierto para que la VPN pueda leer el texto
trap 'exit 0' SIGINT SIGTERM SIGHUP
while true; do
    sleep 3600
done
