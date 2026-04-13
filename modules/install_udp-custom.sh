#!/bin/bash
# MaximusVpsMx - Instalador UDP-CUSTOM v2.0
# Formato compatible: IP:1-65535@usuario:contraseña

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${CYAN}=========================================================${NC}"
echo -e "${YELLOW}        INSTALADOR UDP-CUSTOM v2.0 (AUTH MODE)${NC}"
echo -e "${CYAN}=========================================================${NC}"
echo -e "${WHITE} Formato de conexión del cliente:${NC}"
echo -e "${CYAN} IP:1-65535@usuario:contraseña${NC}"
echo -e "${CYAN}=========================================================${NC}"

# Puerto de escucha
read -p " Puerto UDP (Default 1, rango completo 1-65535): " udp_port
[ -z "$udp_port" ] && udp_port=1

# Contraseña(s) de autenticación
echo -e "\n${YELLOW} Puedes agregar múltiples contraseñas separadas por coma.${NC}"
echo -e "${CYAN} Ejemplo: pass1,pass2,pass3${NC}"
read -p " Contraseña(s) (Default: maximus): " udp_pass
[ -z "$udp_pass" ] && udp_pass="maximus"

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

# Fallback
if [ ! -f "$UDP_DIR/udp-custom" ] || [ ! -s "$UDP_DIR/udp-custom" ]; then
    echo -e "${YELLOW}[+] Intentando fuente alternativa...${NC}"
    wget -qO "$UDP_DIR/udp-custom" "https://github.com/AmineMrabet12/UDP-Custom-V3/releases/latest/download/udp-custom-linux-${BIN_ARCH}" 2>/dev/null
fi

if [ ! -f "$UDP_DIR/udp-custom" ] || [ ! -s "$UDP_DIR/udp-custom" ]; then
    echo -e "${RED}❌ Error: No se pudo descargar el binario.${NC}"
    sleep 3
    exit 1
fi

chmod +x "$UDP_DIR/udp-custom"

# Construir lista de contraseñas en formato JSON
PASS_JSON=""
IFS=',' read -ra PASS_ARRAY <<< "$udp_pass"
for i in "${!PASS_ARRAY[@]}"; do
    p=$(echo "${PASS_ARRAY[$i]}" | xargs) # trim spaces
    if [ $i -eq 0 ]; then
        PASS_JSON="\"$p\""
    else
        PASS_JSON="$PASS_JSON, \"$p\""
    fi
done

# Generar configuración con autenticación por contraseñas
echo -e "${GREEN}[+] Generando configuración (puerto $udp_port, rango 1-65535)...${NC}"
cat > "$UDP_DIR/config.json" << UDPEOF
{
    "listen": ":$udp_port",
    "stream_buffer": 33554432,
    "receive_buffer": 33554432,
    "auth": {
        "mode": "passwords",
        "passwords": [$PASS_JSON]
    }
}
UDPEOF

# Matar procesos previos
fuser -k "$udp_port/udp" 2>/dev/null
fuser -k "$udp_port/tcp" 2>/dev/null
killall -9 udp-custom 2>/dev/null

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
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF

# Abrir puertos en firewall (rango completo para UDP)
ufw allow 1:65535/udp 2>/dev/null

# Activar y arrancar
systemctl daemon-reload
systemctl enable --now udp-custom 2>/dev/null
systemctl restart udp-custom 2>/dev/null

# Obtener IP del servidor
SERVER_IP=$(wget -qO- ipv4.icanhazip.com 2>/dev/null)
[ -z "$SERVER_IP" ] && SERVER_IP="TU_IP"

# Verificación
sleep 2
if systemctl is-active --quiet udp-custom; then
    echo -e "\n${GREEN}=========================================================${NC}"
    echo -e "${GREEN} ✅ UDP-CUSTOM INSTALADO CORRECTAMENTE${NC}"
    echo -e "${GREEN}=========================================================${NC}"
    echo -e "${CYAN} Puerto:      $udp_port (Rango: 1-65535)${NC}"
    echo -e "${CYAN} Contraseñas: $udp_pass${NC}"
    echo -e "${GREEN}=========================================================${NC}"
    echo -e "${YELLOW} 📋 CONFIGURACIÓN PARA EL CLIENTE:${NC}"
    echo -e "${WHITE} ${SERVER_IP}:1-65535@usuario:${PASS_ARRAY[0]}${NC}"
    echo -e "${GREEN}=========================================================${NC}"
    echo -e "${CYAN} Copia esa línea en tu app (HTTP Custom / HA Tunnel).${NC}"
else
    echo -e "\n${RED}=========================================================${NC}"
    echo -e "${RED} ⚠️ UDP-CUSTOM no arrancó. Verifica con:${NC}"
    echo -e "${YELLOW} systemctl status udp-custom${NC}"
    echo -e "${RED}=========================================================${NC}"
fi
sleep 3
