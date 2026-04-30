#!/bin/bash
# Maximus Dynamic PAM Banner

# El módulo pam_exec exporta la variable PAM_USER con el nombre del usuario
username="$PAM_USER"

# Si no hay usuario, salir silenciosamente
[ -z "$username" ] && exit 0

exp_date=$(grep "^${username}:" /etc/MaximusVpsMx/users.db 2>/dev/null | cut -d: -f3 2>/dev/null)

echo ""
echo -e "🌟 SERVIDORES PREMIUM 🌟"
echo -e "👑 VIP TEAM LATAM 👑"
echo -e "💎 LA MEJOR CALIDAD 💎"
echo ""
echo -e "⚡ DETALLES DE SU SERVIDOR ⚡"
echo ""
echo -e "🛡️ USUARIO : $username"
echo -e "👥 GRUPO   : Premium"

if [ -n "$exp_date" ]; then
    today=$(date +%s)
    exp=$(date -d "$exp_date" +%s)
    days_left=$(( (exp - today) / 86400 ))
    
    # Formatear la fecha a 'May 02, 2026'
    formatted_date=$(date -d "$exp_date" "+%b %d, %Y")
    
    echo -e "📅 VALIDO  : $formatted_date"
    echo -e "⏳ RESTAN  : $days_left DIAS"
else
    echo -e "📅 VALIDO  : Ilimitado"
    echo -e "⏳ RESTAN  : Ilimitados"
fi

echo ""

# Finalizar inmediatamente para no retrasar la conexión SSH
exit 0
