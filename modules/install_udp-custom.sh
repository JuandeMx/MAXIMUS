#!/bin/bash
# MaximusVpsMx - Instalador UDP-CUSTOM v2.1
# Autenticación: Usa los mismos usuarios SSH del panel
# Formato cliente: IP:1-65535@usuarioSSH:contraseñaSSH

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${CYAN}=========================================================${NC}"
echo -e "${YELLOW}         INSTALADOR UDP-CUSTOM (TUNNELING UDP)${NC}"
echo -e "${CYAN}=========================================================${NC}"
echo -e "${WHITE} Los clientes usan sus credenciales SSH del panel.${NC}"
echo -e "${CYAN} Formato: IP:1-65535@usuarioSSH:contraseñaSSH${NC}"
echo -e "${CYAN}=========================================================${NC}"

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

# Descargar el binario - Lógica Robusta (Curl + Wget)
echo -e "${YELLOW}[+] Descargando UDP-Custom ($BIN_ARCH)...${NC}"
if curl -sL -o "$UDP_DIR/udp-custom" "https://github.com/Haris131/UDP-Custom/raw/main/udp-custom-linux-${BIN_ARCH}"; then
    echo -e "${GREEN}[✔] Descarga primaria exitosa (Haris).${NC}"
elif wget -q -O "$UDP_DIR/udp-custom" "https://github.com/prjkt-nv404/UDP-Custom-Installer-Manager/raw/main/bin/udp-custom-linux-${BIN_ARCH}"; then
    echo -e "${GREEN}[✔] Descarga secundaria exitosa (Mirror).${NC}"
else
    echo -e "${RED}[✘] No se pudo descargar desde ninguna fuente.${NC}"
fi

if [ ! -f "$UDP_DIR/udp-custom" ] || [ ! -s "$UDP_DIR/udp-custom" ]; then
    echo -e "${RED}❌ Error: No se pudo descargar el binario.${NC}"
    sleep 3
    exit 1
fi

chmod +x "$UDP_DIR/udp-custom"

# Generar configuración SIN autenticación propia (usa SSH del panel)
echo -e "${GREEN}[+] Generando configuración (rango completo 1-65535)...${NC}"
cat > "$UDP_DIR/config.json" << UDPEOF
{
    "listen": ":36712",
    "stream_buffer": 33554432,
    "receive_buffer": 33554432,
    "auth": {
        "mode": "disabled"
    }
}
UDPEOF

# Matar procesos previos y limpiar sockets
echo -e "${GREEN}[+] Limpiando procesos y sockets previos...${NC}"
pkill -9 udp-custom 2>/dev/null
killall -9 udp-custom 2>/dev/null
fuser -k 36712/udp 2>/dev/null

# Crear servicio systemd con Logs de Depuración
echo -e "${GREEN}[+] Creando servicio systemd con registros de error...${NC}"
cat > /etc/systemd/system/udp-custom.service << EOF
[Unit]
Description=MaximusVpsMx UDP-Custom Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$UDP_DIR
ExecStartPre=/usr/bin/pkill -9 udp-custom || true
ExecStart=${UDP_DIR}/udp-custom server
Restart=always
RestartSec=3
LimitNOFILE=infinity
StandardOutput=append:/var/log/MaximusVpsMx/udp-custom.log
StandardError=append:/var/log/MaximusVpsMx/udp-custom.log

[Install]
WantedBy=multi-user.target
EOF

# Abrir puertos en firewall
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
    echo -e "${CYAN} Rango de puertos: 1-65535${NC}"
    echo -e "${CYAN} Autenticación:    Usuarios SSH del Panel${NC}"
    echo -e "${GREEN}---------------------------------------------------------${NC}"
    echo -e "${YELLOW} 📋 CONFIGURACIÓN PARA EL CLIENTE:${NC}"
    echo -e "${WHITE} ${SERVER_IP}:1-65535@USUARIO_SSH:CONTRASEÑA_SSH${NC}"
    echo -e "${GREEN}=========================================================${NC}"
else
    echo -e "\n${RED}=========================================================${NC}"
    echo -e "${RED} ⚠️ UDP-CUSTOM no arrancó. Verifica con:${NC}"
    echo -e "${YELLOW} systemctl status udp-custom${NC}"
    echo -e "${RED}=========================================================${NC}"
fi
sleep 3
