#!/bin/bash
# MaximusVpsMx - Instalador WS-EPRO (Python Engine)

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${CYAN}=======================================================${NC}"
echo -e "${YELLOW}        🔌 INSTALADOR WS-EPRO (MAXIMUS ENGINE)${NC}"
echo -e "${CYAN}=======================================================${NC}"
echo -e " Este proxy envolverá tráfico SSH en WebSockets puros."

# Puertos por defecto
DEFAULT_PORT=80
DEFAULT_TARGET=44

# Autodetección de backend sugerido
if systemctl is-active --quiet dropbear; then
    DEFAULT_TARGET=$(grep "DROPBEAR_PORT=" /etc/default/dropbear | cut -d= -f2 | tr -d '"')
    [ -z "$DEFAULT_TARGET" ] && DEFAULT_TARGET=44
fi

read -p " Puerto para escuchar WS (Recomendado 80 o 8080) [$DEFAULT_PORT]: " WS_PORT
[ -z "$WS_PORT" ] && WS_PORT=$DEFAULT_PORT

read -p " Puerto destino (Dropbear/OpenSSH) [$DEFAULT_TARGET]: " WS_TARGET
[ -z "$WS_TARGET" ] && WS_TARGET=$DEFAULT_TARGET

# Detectar choque de puertos
if netstat -tuln | grep -q ":$WS_PORT "; then
    echo -e "\n${RED}⚠️  ERROR FATAL: El puerto $WS_PORT ya está siendo usado por otro servicio.${NC}"
    echo -e "${YELLOW}Revisa si mx-proxy o apache ya están corriendo ahí.${NC}"
    sleep 3
    exit 1
fi

echo -e "\n${GREEN}[+] Instalando Maximus WS-Engine...${NC}"
apt-get update -y > /dev/null 2>&1
apt-get install -y python3 > /dev/null 2>&1

mkdir -p /etc/MaximusVpsMx/core

# Descargar desde la bóveda local si existe, si no, se asume que se clonó con la rama main
if [ ! -f "/etc/MaximusVpsMx/core/ws-epro.py" ]; then
    wget -qO /etc/MaximusVpsMx/core/ws-epro.py "https://raw.githubusercontent.com/JuandeMx/MAXIMUS/main/core/ws-epro.py"
fi
chmod +x /etc/MaximusVpsMx/core/ws-epro.py

echo -e "${GREEN}[+] Configurando servicio systemd...${NC}"
cat > /etc/systemd/system/ws-epro.service << EOF
[Unit]
Description=MaximusVpsMx WS-EPRO Proxy
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/MaximusVpsMx
ExecStart=/usr/bin/python3 /etc/MaximusVpsMx/core/ws-epro.py $WS_PORT $WS_TARGET
Restart=always
RestartSec=3
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF

# Reiniciar y habilitar
systemctl daemon-reload
systemctl enable --now ws-epro > /dev/null 2>&1
systemctl restart ws-epro

sleep 2
if systemctl is-active --quiet ws-epro; then
    echo -e "\n${GREEN}=======================================================${NC}"
    echo -e "${GREEN} ✅ WS-EPRO INSTALADO SATISFACTORIAMENTE${NC}"
    echo -e "${CYAN} Puerto Entrada (Payload): $WS_PORT${NC}"
    echo -e "${CYAN} Puerto Destino (Backend):  $WS_TARGET${NC}"
    echo -e "${GREEN}=======================================================${NC}"
else
    echo -e "\n${RED}=======================================================${NC}"
    echo -e "${RED} ⚠️ Fallo al iniciar el servicio WS-EPRO.${NC}"
    echo -e "${RED}=======================================================${NC}"
fi
sleep 3
