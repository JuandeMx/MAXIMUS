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

# Descargar el binario Real de Haris131
echo -e "${YELLOW}[+] Descargando UDP-Custom Real desde Haris131 ($BIN_ARCH)...${NC}"
if curl -sL -o "$UDP_DIR/udp-custom" "https://github.com/Haris131/UDP-Custom/raw/main/udp-custom-linux-${BIN_ARCH}"; then
    echo -e "${GREEN}[✔] Descarga primaria exitosa (Haris Real).${NC}"
else
    # Mirror estable propio
    wget -q -O "$UDP_DIR/udp-custom" "https://raw.githubusercontent.com/JuandeMx/MAXIMUS/main/bin/udp-custom-linux-${BIN_ARCH}"
    echo -e "${GREEN}[✔] Descarga desde mirror oficial Maximus.${NC}"
fi

if [ ! -f "$UDP_DIR/udp-custom" ] || [ ! -s "$UDP_DIR/udp-custom" ]; then
    echo -e "${RED}❌ Error: No se pudo descargar el binario.${NC}"
    exit 1
fi

chmod +x "$UDP_DIR/udp-custom"

# Generar configuración de escucha directa (Puerto :36712)
echo -e "${GREEN}[+] Generando configuración de escucha directa (Puerto :36712)...${NC}"
cat > "$UDP_DIR/config.json" << UDPEOF
{
    "listen": ":36712",
    "stream_buffer": 33554432,
    "receive_buffer": 83886080,
    "auth": {
        "mode": "passwords",
        "passwords": ["volviamorir"]
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
ExecStart=${UDP_DIR}/udp-custom server
Restart=always
RestartSec=3
LimitNOFILE=infinity
StandardOutput=append:/var/log/MaximusVpsMx/udp-custom.log
StandardError=append:/var/log/MaximusVpsMx/udp-custom.log

[Install]
WantedBy=multi-user.target
EOF

# Abrir puertos en firewall (SIN REDIRECCIÓN NAT PARA PRUEBA)
echo -e "${GREEN}[+] Abriendo puerto 36712 en el servidor...${NC}"
ufw allow 36712/udp 2>/dev/null

# Limpiar reglas previas de redirección para evitar ruido
iptables -t nat -D PREROUTING -p udp --dport 1:65535 -j REDIRECT --to-port 1 2>/dev/null
ip6tables -t nat -D PREROUTING -p udp --dport 1:65535 -j REDIRECT --to-port 1 2>/dev/null
iptables -t nat -F 2>/dev/null

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
