#!/bin/bash
# Maximus Dynamic HTML Shell

username=$USER
exp_date=$(grep "^${username}:" /etc/MaximusVpsMx/users.db | cut -d: -f3 2>/dev/null)

cat << 'EOF'
<br><br>
<center>
  <h1><font color="red" size="10"><b>SERVIDORES PREMIUM</b></font></h1>
  <br>
  <h1>
    <font color="#74ACDF"><b>VIP </b></font>
    <font color="white"><b>TEAM </b></font>
    <font color="#74ACDF"><b>LATAM</b></font>
  </h1>
  <br>
  <h1><font color="white" size="10"><b>LA MEJOR CALIDAD</b></font></h1>
EOF

if [ -n "$exp_date" ]; then
    today=$(date +%s)
    exp=$(date -d "$exp_date" +%s)
    days_left=$(( (exp - today) / 86400 ))
    
    echo "  <br>"
    echo "  <h2><font color=\"yellow\"><b>👤 Usuario: $username</b></font></h2>"
    echo "  <h2><font color=\"yellow\"><b>📅 Vence: $exp_date</b></font></h2>"
    
    if [ "$days_left" -lt 0 ]; then
        echo "  <h2><font color=\"red\"><b>❌ ESTADO: EXPIRADO</b></font></h2>"
    elif [ "$days_left" -eq 0 ]; then
        echo "  <h2><font color=\"orange\"><b>⚠️ ESTADO: VENCE HOY</b></font></h2>"
    else
        echo "  <h2><font color=\"#00FF00\"><b>✅ RESTAN: $days_left Días</b></font></h2>"
    fi
else
    echo "  <br>"
    echo "  <h2><font color=\"yellow\"><b>👤 Usuario: $username</b></font></h2>"
    echo "  <h2><font color=\"#00FF00\"><b>✅ RESTAN: Ilimitado</b></font></h2>"
fi

echo "</center>"
echo "<br><br>"

# Mantener el canal SSH abierto para que la VPN pueda leer el texto
trap 'exit 0' SIGINT SIGTERM SIGHUP
while true; do
    sleep 3600
done
