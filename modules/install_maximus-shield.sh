#!/bin/bash
# MaximusVpsMx - Master Installer: MAXIMUS-SHIELD 🛡️

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

KEY_FILE="/etc/MaximusVpsMx/shield.key"
mkdir -p /etc/MaximusVpsMx/core

# Generar llave única del servidor si no existe
if [ ! -f "$KEY_FILE" ]; then
    tr -dc A-Za-z0-9 </dev/urandom | head -c 32 > "$KEY_FILE"
fi

SECRET_KEY=$(cat "$KEY_FILE")

# Función de Cifrado (XOR + Base64) - Herramienta Interna
encrypt_sni() {
    local sni="$1"
    local key="$SECRET_KEY"
    python3 -c "
import base64
def xor_crypt(data, key):
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
sni = '$sni'.encode('utf-8')
key = '$key'.encode('utf-8')
encrypted = base64.b64encode(xor_crypt(sni, key)).decode('utf-8')
print('MAX-' + encrypted)
"
}

clear
echo -e "${CYAN}=======================================================${NC}"
echo -e "${WHITE}        🛡️  INSTALADOR: MAXIMUS-SHIELD ELITE 🛡️${NC}"
echo -e "${CYAN}=======================================================${NC}"
echo -e " El protocolo más seguro y privado para tu Panel."

# Gestión de Puertos
DEFAULT_PORT=80
DEFAULT_TARGET=44

if systemctl is-active --quiet dropbear; then
    DEFAULT_TARGET=$(grep "DROPBEAR_PORT=" /etc/default/dropbear | cut -d= -f2 | tr -d '"')
    [ -z "$DEFAULT_TARGET" ] && DEFAULT_TARGET=44
fi

read -p " 🛡️ Puerto para MAXIMUS-SHIELD [$DEFAULT_PORT]: " WS_PORT
[ -z "$WS_PORT" ] && WS_PORT=$DEFAULT_PORT

read -p " 🛡️ Puerto Destino (Backend) [$DEFAULT_TARGET]: " WS_TARGET
[ -z "$WS_TARGET" ] && WS_TARGET=$DEFAULT_TARGET

# Chequeo de Puerto
if netstat -tuln | grep -q ":$WS_PORT "; then
    echo -e "\n${RED}❌ ERROR: El puerto $WS_PORT está ocupado.${NC}"
    sleep 2; exit 1
fi

echo -e "\n${GREEN}[+] Desplegando Shield Engine v1.0...${NC}"

# Descarga/Copia del motor
cp d:/mipanel/MaximusVpsMx/core/maximus-shield.py /etc/MaximusVpsMx/core/maximus-shield.py 2>/dev/null
if [ ! -f "/etc/MaximusVpsMx/core/maximus-shield.py" ]; then
    wget -qO /etc/MaximusVpsMx/core/maximus-shield.py "https://raw.githubusercontent.com/JuandeMx/MAXIMUS/main/core/maximus-shield.py"
fi
chmod +x /etc/MaximusVpsMx/core/maximus-shield.py

# Crear servicio
cat > /etc/systemd/system/maximus-shield.service << EOF
[Unit]
Description=MaximusVpsMx Shield Elite Proxy
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/MaximusVpsMx
ExecStart=/usr/bin/python3 /etc/MaximusVpsMx/core/maximus-shield.py $WS_PORT $WS_TARGET
Restart=always
RestartSec=3
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now maximus-shield > /dev/null 2>&1
systemctl restart maximus-shield

sleep 2
if systemctl is-active --quiet maximus-shield; then
    echo -e "\n${GREEN}=======================================================${NC}"
    echo -e "${GREEN} ✅ MAXIMUS-SHIELD ACTIVADO EXITOSAMENTE${NC}"
    echo -e "${CYAN} Entrada: $WS_PORT  |  Backend: $WS_TARGET${NC}"
    echo -e "${GREEN}=======================================================${NC}"
else
    echo -e "\n${RED} ❌ Error en el arranque del Shield.${NC}"
fi
sleep 2
