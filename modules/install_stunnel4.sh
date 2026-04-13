#!/bin/bash
# Instalador Dinámico Stunnel4 SSL

echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m             INSTALADOR STUNNEL (SSL/TLS)\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
read -p " ¿En qué puerto público deseas recibir SSL? (ej: 443): " ssl_port
if [[ -z "$ssl_port" ]]; then ssl_port=443; fi

read -p " ¿Hacia qué puerto local debe enviarse el tráfico? (ej: 80 para proxy, 22 para ssh): " fwd_port
if [[ -z "$fwd_port" ]]; then fwd_port=80; fi

echo -e "\n\e[1;32m[+] Configurando Stunnel4 SSL (Escucha $ssl_port -> Redirige a $fwd_port)...\e[0m"

DEBIAN_FRONTEND=noninteractive apt-get install -y stunnel4 2>/dev/null

cat > /etc/stunnel/stunnel.conf << EOF
; MaximusVpsMx - Stunnel SSL Configuration
cert = /etc/stunnel/stunnel.pem
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1
socket = l:SO_KEEPALIVE=1
socket = r:SO_KEEPALIVE=1
TIMEOUTclose = 0
TIMEOUTconnect = 10
TIMEOUTidle = 600
output = /var/log/MaximusVpsMx/stunnel.log
syslog = no

[ssh]
client = no
accept = $ssl_port
connect = 127.0.0.1:$fwd_port
EOF

# Generar certificado si no existe
if [ ! -f /etc/stunnel/stunnel.pem ]; then
    openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -sha256 -subj "/CN=MaximusVpsMx/O=Maximus/C=US" -keyout /etc/stunnel/stunnel.pem -out /etc/stunnel/stunnel.pem >/dev/null 2>&1
    chmod 600 /etc/stunnel/stunnel.pem
fi

sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4 2>/dev/null

ufw allow ${ssl_port}/tcp 2>/dev/null

systemctl daemon-reload
systemctl enable --now stunnel4 2>/dev/null
systemctl restart stunnel4 2>/dev/null
echo -e "\e[1;32m[✓] Stunnel interactuando exitosamente en el puerto $ssl_port.\e[0m"
sleep 3
