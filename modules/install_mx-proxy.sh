#!/bin/bash
# Instalador Dinámico Proxy Python

echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m          INSTALADOR PROXY PYTHON (CLOUDFRONT)\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
proxy_port=$1
if [[ -z "$proxy_port" ]]; then
    read -p " ¿En qué puerto deseas instalar el Proxy Python? (ej: 80): " proxy_port
fi

if [[ -z "$proxy_port" ]]; then
    echo -e "\e[1;31m❌ Cancelado. Puerto inválido.\e[0m"
    sleep 2
    exit 1
fi

echo -e "\n\e[1;32m[+] Configurando Proxy Python en el puerto $proxy_port...\e[0m"

# Creamos el servicio systemd dinámicamente con el puerto
cat > /etc/systemd/system/mx-proxy.service << EOF
[Unit]
Description=MaximusVpsMx Python Proxy Port $proxy_port
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/MaximusVpsMx/core
ExecStart=/usr/bin/python3 /etc/MaximusVpsMx/core/PDirect.py $proxy_port
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Abrir en el firewall
ufw allow ${proxy_port}/tcp 2>/dev/null

# Aplicar servicio
systemctl daemon-reload
systemctl enable --now mx-proxy 2>/dev/null
systemctl restart mx-proxy 2>/dev/null

echo -e "\e[1;32m[✓] Proxy Python instalado y activo en el puerto $proxy_port.\e[0m"
sleep 3
