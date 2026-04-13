#!/bin/bash
# Instalador Dinámico Stunnel4 SSL + Cadena Automática

echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m        INSTALADOR STUNNEL SSL (CADENA COMPLETA)\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;37m Este instalador configura automáticamente:\e[0m"
echo -e "\e[1;32m   HTTP Custom → Stunnel(SSL) → Proxy Python → SSH\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
read -p " ¿En qué puerto público deseas recibir SSL? (ej: 443): " ssl_port
if [[ -z "$ssl_port" ]]; then ssl_port=443; fi

echo -e "\n\e[1;32m[1/4] Verificando Proxy Python en puerto 80...\e[0m"

# === AUTO-INSTALAR PROXY PYTHON SI NO ESTÁ CORRIENDO ===
if ! systemctl is-active --quiet mx-proxy; then
    echo -e "\e[1;33m    → Proxy Python NO detectado. Instalando automáticamente en puerto 80...\e[0m"
    
    cat > /etc/systemd/system/mx-proxy.service << EOF
[Unit]
Description=MaximusVpsMx Python Proxy Port 80
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/MaximusVpsMx/core
ExecStart=/usr/bin/python3 /etc/MaximusVpsMx/core/PDirect.py 80
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    ufw allow 80/tcp 2>/dev/null
    systemctl daemon-reload
    systemctl enable --now mx-proxy 2>/dev/null
    echo -e "\e[1;32m    ✓ Proxy Python activo en puerto 80.\e[0m"
else
    echo -e "\e[1;32m    ✓ Proxy Python ya está corriendo.\e[0m"
fi

echo -e "\e[1;32m[2/4] Configurando Stunnel SSL en puerto $ssl_port...\e[0m"

DEBIAN_FRONTEND=noninteractive apt-get install -y stunnel4 2>/dev/null

cat > /etc/stunnel/stunnel.conf << EOF
; MaximusVpsMx - Stunnel SSL Configuration (Auto-Chain)
cert = /etc/stunnel/stunnel.pem
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1
socket = l:SO_KEEPALIVE=1
socket = r:SO_KEEPALIVE=1
TIMEOUTclose = 0
TIMEOUTconnect = 10
TIMEOUTidle = 600

[ssh]
client = no
accept = $ssl_port
connect = 127.0.0.1:80
EOF

echo -e "\e[1;32m[3/4] Generando certificado SSL...\e[0m"

if [ ! -f /etc/stunnel/stunnel.pem ]; then
    openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -sha256 -subj "/CN=MaximusVpsMx/O=Maximus/C=US" -keyout /etc/stunnel/stunnel.pem -out /etc/stunnel/stunnel.pem >/dev/null 2>&1
    chmod 600 /etc/stunnel/stunnel.pem
    echo -e "\e[1;32m    ✓ Certificado SSL generado.\e[0m"
else
    echo -e "\e[1;32m    ✓ Certificado SSL ya existe.\e[0m"
fi

sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4 2>/dev/null

ufw allow ${ssl_port}/tcp 2>/dev/null

echo -e "\e[1;32m[4/4] Activando servicios...\e[0m"

killall stunnel4 2>/dev/null || true
systemctl daemon-reload
systemctl enable --now stunnel4 2>/dev/null
systemctl restart stunnel4 2>/dev/null
systemctl restart mx-proxy 2>/dev/null

echo -e "\n\e[1;36m=========================================================\e[0m"
echo -e "\e[1;32m[✓] CADENA SSL COMPLETA ACTIVADA:\e[0m"
echo -e "\e[1;37m    Cliente → Stunnel(:$ssl_port) → Proxy(:80) → SSH(:22)\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
sleep 3
