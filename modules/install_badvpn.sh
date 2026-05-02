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
    echo -e "${YELLOW}[+] Instalando dependencias de compilación...${NC}"
    DEBIAN_FRONTEND=noninteractive apt-get install -y cmake make gcc build-essential git 2>/dev/null
    echo -e "${YELLOW}[+] Clonando repositorio de BadVPN...${NC}"
    rm -rf /tmp/badvpn
    git clone https://github.com/ambrop72/badvpn.git /tmp/badvpn >/dev/null 2>&1
    if [ ! -d /tmp/badvpn ]; then
        echo -e "${RED}❌ Error al clonar el repositorio. Verifica tu conexión.${NC}"
        exit 1
    fi
    cd /tmp/badvpn
    echo -e "${YELLOW}[+] Compilando BadVPN-udpgw (esto puede tardar un momento)...${NC}"
    mkdir build && cd build
    cmake .. -DBUILD_NOTHING_BY_DEFAULT=1 -DBUILD_UDPGW=1 >/dev/null 2>&1
    make install >/dev/null 2>&1
    cd /root
    rm -rf /tmp/badvpn
fi

if [ ! -f /usr/local/bin/badvpn-udpgw ]; then
    echo -e "${RED}❌ Error: No se pudo compilar/instalar badvpn-udpgw.${NC}"
    exit 1
fi

cat > /etc/systemd/system/badvpn.service << EOF
[Unit]
Description=MaximusVpsMx BadVPN UDPGW Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/badvpn-udpgw --listen-addr 0.0.0.0:$bad_port --max-clients 1000 --max-connections-for-client 10
Restart=always

[Install]
WantedBy=multi-user.target
EOF

ufw allow ${bad_port}/udp 2>/dev/null
ufw allow ${bad_port}/tcp 2>/dev/null

systemctl daemon-reload
systemctl enable --now badvpn 2>/dev/null
systemctl restart badvpn 2>/dev/null

if systemctl is-active --quiet badvpn; then
    echo -e "\e[1;32m[✓] BadVPN UDP activo en el puerto $bad_port.\e[0m"
else
    echo -e "\e[1;31m[❌] El servicio BadVPN no pudo iniciarse. Revisa los logs.${NC}"
fi
sleep 3

