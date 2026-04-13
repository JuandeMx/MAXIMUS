#!/bin/bash
# Instalador Dinámico BadVPN-UDPGW

echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m          INSTALADOR BADVPN UDPGW (GAMING)\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
read -p " ¿En qué puerto deseas procesar UDPGW? (Por defecto 7300, presiona Enter para Default): " bad_port

if [[ -z "$bad_port" ]]; then
    bad_port=7300
fi

echo -e "\n\e[1;32m[+] Compilando/Configurando BadVPN-udpgw en puerto $bad_port...\e[0m"

# Si no existe el binario, lo instalamos compilándolo
if [ ! -f /usr/local/bin/badvpn-udpgw ]; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y cmake make gcc build-essential 2>/dev/null
    git clone https://github.com/ambrop72/badvpn.git /tmp/badvpn 2>/dev/null
    cd /tmp/badvpn
    cmake -DBUILD_NOTHING_BY_DEFAULT=1 -DBUILD_UDPGW=1 >/dev/null 2>&1
    make install >/dev/null 2>&1
    rm -rf /tmp/badvpn
fi

cat > /etc/systemd/system/badvpn.service << EOF
[Unit]
Description=MaximusVpsMx BadVPN UDPGW Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/badvpn-udpgw --listen-addr 127.0.0.1:$bad_port --max-clients 1000 --max-connections-for-client 10
Restart=always

[Install]
WantedBy=multi-user.target
EOF

ufw allow ${bad_port}/udp 2>/dev/null

systemctl daemon-reload
systemctl enable --now badvpn 2>/dev/null
systemctl restart badvpn 2>/dev/null
echo -e "\e[1;32m[✓] BadVPN UDP activo en el puerto local $bad_port.\e[0m"
sleep 3
