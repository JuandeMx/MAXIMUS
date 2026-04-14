#!/bin/bash
# MaximusVpsMx - X-UI Native Offline Installer
# Despliega el panel web X-UI desde binarios precargados

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

clear
echo -e "${CYAN}=======================================================${NC}"
echo -e "${YELLOW}       INSTALANDO PANEL WEB X-UI (OFFLINE)${NC}"
echo -e "${CYAN}=======================================================${NC}"

if [ ! -f /etc/MaximusVpsMx/modules/offline/x-ui-linux-amd64.tar.gz ]; then
    echo -e "${RED}[X] Error crítico: El paquete nativo de X-UI no se encontró.${NC}"
    echo -e "${YELLOW}Asegúrate de que la carpeta modules/offline/ contenga x-ui-linux-amd64.tar.gz${NC}"
    sleep 3
    exit 1
fi

echo -e "${YELLOW}[+] Extrayendo binarios nativos...${NC}"
cd /usr/local/
tar zxvf /etc/MaximusVpsMx/modules/offline/x-ui-linux-amd64.tar.gz >/dev/null 2>&1
chmod +x /usr/local/x-ui/x-ui /usr/local/x-ui/bin/* /usr/local/x-ui/x-ui.sh

echo -e "${YELLOW}[+] Configurando entorno de ejecución...${NC}"
cp /usr/local/x-ui/x-ui.service /etc/systemd/system/x-ui.service
cp /usr/local/x-ui/x-ui.sh /usr/bin/x-ui
chmod +x /usr/bin/x-ui

echo -e "${YELLOW}[+] Generando Certificado TLS/SSL Autenticado...${NC}"
mkdir -p /etc/x-ui/
openssl req -x509 -newkey rsa:2048 -days 3650 -nodes -sha256 -subj "/CN=MaximusVpsMx/O=Maximus/C=US" -keyout /etc/x-ui/server.key -out /etc/x-ui/server.crt >/dev/null 2>&1

echo -e "${YELLOW}[+] Iniciando bases de datos y demonio X-UI...${NC}"
systemctl daemon-reload
systemctl enable x-ui > /dev/null 2>&1
systemctl start x-ui > /dev/null 2>&1
sleep 3

apt-get install -y sqlite3 >/dev/null 2>&1
chmod 644 /etc/x-ui/server.crt /etc/x-ui/server.key
sqlite3 /etc/x-ui/x-ui.db "UPDATE settings SET value='/etc/x-ui/server.crt' WHERE key='webCertFile';" >/dev/null 2>&1
sqlite3 /etc/x-ui/x-ui.db "UPDATE settings SET value='/etc/x-ui/server.key' WHERE key='webKeyFile';" >/dev/null 2>&1

systemctl restart x-ui > /dev/null 2>&1
sleep 1

PORT=$(/usr/local/x-ui/x-ui setting -show 2>/dev/null | grep -Po 'webPort: \K[0-9]+')
if [ -z "$PORT" ]; then
    PORT=54321
fi

echo -e "${YELLOW}[+] Abriendo puerto $PORT en el firewall...${NC}"
ufw allow $PORT/tcp >/dev/null 2>&1

IP=$(wget -qO- ipv4.icanhazip.com 2>/dev/null)
[ -z "$IP" ] && IP="127.0.0.1"

clear
echo -e "${CYAN}=======================================================${NC}"
echo -e "${GREEN} ✅ PANEL X-UI INSTALADO EXITOSAMENTE${NC}"
echo -e "${CYAN}=======================================================${NC}"
echo -e "${YELLOW}▶ URL de Acceso:   ${WHITE}https://$IP:$PORT/${NC}"
echo -e "${YELLOW}▶ Usuario Inicial: ${WHITE}admin${NC}"
echo -e "${YELLOW}▶ Clave Inicial:   ${WHITE}admin${NC}"
echo -e "${CYAN}=======================================================${NC}"
echo -e "${RED}⚠️ IMPORTANTE: Por seguridad, cambia estas credenciales${NC}"
echo -e "${RED}   inmediatamente desde el propio Panel Web.${NC}"
echo -e "${CYAN}=======================================================${NC}"
echo -e ""
read -p " Presiona Enter para volver..."
