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

# Primero, buscar el binario en la carpeta local del panel para evitar descargas
if [ -f /etc/MaximusVpsMx/bin/badvpn-udpgw ]; then
    echo -e "${GREEN}[+] Instalando BadVPN-udpgw desde la bóveda local del panel...${NC}"
    cp -f /etc/MaximusVpsMx/bin/badvpn-udpgw /usr/local/bin/badvpn-udpgw
    chmod +x /usr/local/bin/badvpn-udpgw
fi

# Si no existe el binario (ej: borrado manual), intentamos compilarlo o usar el fallback de descarga
if [ ! -f /usr/local/bin/badvpn-udpgw ]; then
    echo -e "${YELLOW}[+] Instalando dependencias de compilación...${NC}"
    DEBIAN_FRONTEND=noninteractive apt-get install -y cmake make gcc g++ build-essential git libssl-dev libnss3-dev pkg-config 2>/dev/null
    
    echo -e "${YELLOW}[+] Clonando repositorio de BadVPN...${NC}"
    rm -rf /tmp/badvpn
    git clone https://github.com/ambrop72/badvpn.git /tmp/badvpn >/dev/null 2>&1
    
    if [ -d /tmp/badvpn ]; then
        cd /tmp/badvpn
        echo -e "${YELLOW}[+] Compilando BadVPN-udpgw (esto puede tardar un momento)...${NC}"
        mkdir build && cd build
        cmake .. -DBUILD_NOTHING_BY_DEFAULT=1 -DBUILD_UDPGW=1 >/dev/null 2>&1
        make install >/dev/null 2>&1
        cd /root
        rm -rf /tmp/badvpn
    fi
fi

# Fallback: Si no se pudo compilar, descargar binario verificado
if [ ! -f /usr/local/bin/badvpn-udpgw ]; then
    echo -e "${YELLOW}[⚠️] La compilación falló o no se completó. Descargando binario precompilado alternativo...${NC}"
    curl -sL "https://github.com/daybreakersx/premscript/raw/master/badvpn-udpgw" -o /usr/local/bin/badvpn-udpgw
    chmod +x /usr/local/bin/badvpn-udpgw
fi

if [ ! -f /usr/local/bin/badvpn-udpgw ] && [ ! -f /usr/bin/badvpn-udpgw ]; then
    echo -e "${RED}❌ Error: No se pudo compilar ni descargar badvpn-udpgw.${NC}"
    exit 1
fi

# Asegurar enlace en bin si es necesario
if [ -f /usr/local/bin/badvpn-udpgw ] && [ ! -f /usr/bin/badvpn-udpgw ]; then
    ln -sf /usr/local/bin/badvpn-udpgw /usr/bin/badvpn-udpgw
elif [ -f /usr/bin/badvpn-udpgw ] && [ ! -f /usr/local/bin/badvpn-udpgw ]; then
    ln -sf /usr/bin/badvpn-udpgw /usr/local/bin/badvpn-udpgw
fi

cat > /etc/systemd/system/badvpn.service << EOF
[Unit]
Description=MaximusVpsMx BadVPN UDPGW Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/badvpn-udpgw --listen-addr 0.0.0.0:$bad_port --max-clients 1000 --max-connections-for-client 250 --client-socket-sndbuf 2097152
LimitNOFILE=1000000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

ufw allow ${bad_port}/udp 2>/dev/null
ufw allow ${bad_port}/tcp 2>/dev/null

# Detener agresivamente cualquier cosa en el puerto
systemctl stop badvpn 2>/dev/null
killall -9 badvpn-udpgw 2>/dev/null
pkill -9 badvpn-udpgw 2>/dev/null
fuser -k -9 ${bad_port}/udp 2>/dev/null
fuser -k -9 ${bad_port}/tcp 2>/dev/null
sleep 2

systemctl daemon-reload
systemctl enable badvpn 2>/dev/null
systemctl start badvpn 2>/dev/null

if systemctl is-active --quiet badvpn; then
    echo -e "\e[1;32m[✓] BadVPN UDP activo en el puerto $bad_port.\e[0m"
else
    echo -e "\e[1;31m[❌] El servicio BadVPN no pudo iniciarse. Revisa los logs:\e[0m"
    journalctl -u badvpn -n 10 --no-pager
fi
sleep 3

