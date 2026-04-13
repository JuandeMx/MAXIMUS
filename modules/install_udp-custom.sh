#!/bin/bash
# MaximusVpsMx - Instalador UDP-CUSTOM
# Compatible con HTTP Custom, HTTP Injector, HA Tunnel, etc.

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${CYAN}=========================================================${NC}"
echo -e "${YELLOW}        INSTALADOR UDP-CUSTOM (TUNNELING UDP)${NC}"
echo -e "${CYAN}=========================================================${NC}"

# Puerto configurable
read -p " Puerto UDP (Default 36712, Enter para Default): " udp_port
[ -z "$udp_port" ] && udp_port=36712

echo -e "\n${GREEN}[+] Preparando entorno...${NC}"

# Detectar arquitectura
ARCH=$(uname -m)
case $ARCH in
    x86_64)  BIN_ARCH="amd64"  ;;
    aarch64) BIN_ARCH="arm64"  ;;
    armv7l)  BIN_ARCH="arm"    ;;
    *)       echo -e "${RED}❌ Arquitectura $ARCH no soportada.${NC}"; exit 1 ;;
esac

# Directorio de trabajo
UDP_DIR="/root/udp"
mkdir -p "$UDP_DIR"

# Descargar el binario
echo -e "${YELLOW}[+] Descargando UDP-Custom ($BIN_ARCH)...${NC}"
wget -qO "$UDP_DIR/udp-custom" "https://github.com/EdwardTech/udp-custom/releases/download/v1.1/udp-custom-linux-${BIN_ARCH}" 2>/dev/null

# Fallback: intentar otra fuente si la primera falla
if [ ! -f "$UDP_DIR/udp-custom" ] || [ ! -s "$UDP_DIR/udp-custom" ]; then
    echo -e "${YELLOW}[+] Intentando fuente alternativa...${NC}"
    wget -qO "$UDP_DIR/udp-custom" "https://github.com/AmineMrabet12/UDP-Custom-V3/releases/latest/download/udp-custom-linux-${BIN_ARCH}" 2>/dev/null
fi

if [ ! -f "$UDP_DIR/udp-custom" ] || [ ! -s "$UDP_DIR/udp-custom" ]; then
    echo -e "${RED}❌ Error: No se pudo descargar el binario. Verifica tu conexión.${NC}"
    sleep 3
    exit 1
fi

chmod +x "$UDP_DIR/udp-custom"

# Generar configuración
echo -e "${GREEN}[+] Generando configuración en puerto $udp_port...${NC}"
cat > "$UDP_DIR/config.json" << UDPEOF
{
    "listen": ":$udp_port",
    "stream_buffer": 33554432,
    "receive_buffer": 33554432,
    "auth": {
        "mode": "passwords"
    }
}
UDPEOF

# Matar procesos previos en el puerto
fuser -k "$udp_port/udp" 2>/dev/null
fuser -k "$udp_port/tcp" 2>/dev/null

# Crear servicio systemd
echo -e "${GREEN}[+] Creando servicio systemd...${NC}"
cat > /etc/systemd/system/udp-custom.service << EOF
[Unit]
Description=MaximusVpsMx UDP-Custom Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$UDP_DIR
ExecStart=${UDP_DIR}/udp-custom server
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Abrir puerto en firewall
ufw allow ${udp_port}/udp 2>/dev/null
ufw allow ${udp_port}/tcp 2>/dev/null

# Activar y arrancar
systemctl daemon-reload
systemctl enable --now udp-custom 2>/dev/null
systemctl restart udp-custom 2>/dev/null

# Verificación
sleep 2
if systemctl is-active --quiet udp-custom; then
    echo -e "\n${GREEN}=========================================================${NC}"
    echo -e "${GREEN} ✅ UDP-CUSTOM INSTALADO CORRECTAMENTE${NC}"
    echo -e "${CYAN} Puerto UDP: $udp_port${NC}"
    echo -e "${CYAN} Binario:    $UDP_DIR/udp-custom${NC}"
    echo -e "${CYAN} Config:     $UDP_DIR/config.json${NC}"
    echo -e "${GREEN}=========================================================${NC}"
else
    echo -e "\n${RED}=========================================================${NC}"
    echo -e "${RED} ⚠️ UDP-CUSTOM se instaló pero no arrancó correctamente.${NC}"
    echo -e "${YELLOW} Verifica con: systemctl status udp-custom${NC}"
    echo -e "${RED}=========================================================${NC}"
fi
sleep 3
