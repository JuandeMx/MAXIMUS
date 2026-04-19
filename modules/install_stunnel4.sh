#!/bin/bash
# MaximusVpsMx - Master SSL Installer v4.0 (Agnostic Edition)
# Soporta Modo Directo, Proxy e Híbrido Universal

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

clear
echo -e "${CYAN}=======================================================${NC}"
echo -e "${YELLOW}       🔧 CONFIGURACIÓN SUPREMA: STUNNEL (SSL)${NC}"
echo -e "${CYAN}=======================================================${NC}"
echo -e " Elige la modalidad de conexión para el puerto 443:"
echo -ne "${RED}-------------------------------------------------------${NC}\n"
echo -e " [1] SSL DIRECTO (SSL → SSH)"
echo -e "     ${YELLOW}* El clásico, máxima velocidad, sin Payloads ni Websockets.${NC}"
echo -e " [2] HÍBRIDO MÁXIMO (Puerto 80 + 443)"
echo -e "     ${YELLOW}* Motor Agnóstico Universal usando puerto 80 (Soporta TODAS las combinaciones).${NC}"
echo -e " [3] HÍBRIDO SEGURO (Puerto 8080 + 443)"
echo -e "     ${YELLOW}* Motor Agnóstico Universal usando puerto 8080 (Para evitar conflictos si tienes WebServer en 80).${NC}"
echo -ne "${RED}-------------------------------------------------------${NC}\n"
read -p " Selecciona una opción [1-3]: " mode_opt

# Variables por defecto
SSL_PORT=443
BACKEND_PORT=22
CONNECT_TARGET="127.0.0.1:22"

case $mode_opt in
    1)
        # --- MODO DIRECTO ---
        echo -e "\n${CYAN}▶ MODO DIRECTO SELECCIONADO${NC}"
        read -p " Puerto SSL (Default 443): " SSL_PORT
        [ -z "$SSL_PORT" ] && SSL_PORT=443
        
        # Autodetección rápida
        if systemctl is-active --quiet dropbear; then
            BACKEND_PORT=$(grep "DROPBEAR_PORT=" /etc/default/dropbear | cut -d= -f2 | tr -d '"')
            [ -z "$BACKEND_PORT" ] && BACKEND_PORT=44
        fi
        CONNECT_TARGET="127.0.0.1:$BACKEND_PORT"
        ;;
    2)
        # --- MODO PROXY (SSL + PROXY) ---
        echo -e "\n${CYAN}▶ MODO PROXY/HÍBRIDO SELECCIONADO${NC}"
        read -p " Puerto SSL (Default 443): " SSL_PORT
        [ -z "$SSL_PORT" ] && SSL_PORT=443
        
        # En modo PROXY clásico, el puerto recomendado es 80 (compatibilidad máxima)
        PROXY_PORT=80
        echo -e "${YELLOW}[+] Levantando Proxy en puerto $PROXY_PORT...${NC}"
        bash /etc/MaximusVpsMx/modules/install_mx-proxy.sh $PROXY_PORT > /dev/null 2>&1
        
        CONNECT_TARGET="127.0.0.1:$PROXY_PORT"
        ;;
    3)
        # --- MODO HÍBRIDO (Proxy universal) ---
        echo -e "\n${CYAN}▶ MODO HÍBRIDO SELECCIONADO${NC}"
        read -p " Puerto SSL (Default 443): " SSL_PORT
        [ -z "$SSL_PORT" ] && SSL_PORT=443

        # En híbrido, levantamos el proxy en 8080 para evitar conflictos con 80 si ya lo usan
        PROXY_PORT=8080
        echo -e "${YELLOW}[+] Levantando Proxy Universal en puerto $PROXY_PORT...${NC}"
        bash /etc/MaximusVpsMx/modules/install_mx-proxy.sh $PROXY_PORT > /dev/null 2>&1

        CONNECT_TARGET="127.0.0.1:$PROXY_PORT"
        ;;
    *)
        echo -e "${RED}Opción inválida.${NC}"
        exit 1
        ;;
esac

# --- INSTALACIÓN Y LIMPIEZA NUCLEAR ---
echo -e "\n${YELLOW}[+] Limpieza de puerto $SSL_PORT y aplicación SSL...${NC}"
fuser -k "$SSL_PORT/tcp" 2>/dev/null
apt-get install stunnel4 -y > /dev/null 2>&1

# Asegurar logs
mkdir -p /var/log/stunnel4
chown stunnel4:stunnel4 /var/log/stunnel4

# Generar Configuración
mkdir -p /etc/stunnel
cat > /etc/stunnel/stunnel.conf << EOF
cert = /etc/stunnel/stunnel.pem
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1
socket = l:SO_KEEPALIVE=1
socket = r:SO_KEEPALIVE=1
TIMEOUTclose = 0
TIMEOUTconnect = 10
TIMEOUTidle = 600

# Compatibilidad Suprema
sslVersion = all
options = NO_SSLv2
options = NO_SSLv3
ciphers = HIGH:!aNULL:!MD5

[maximus-ssl]
client = no
accept = $SSL_PORT
connect = $CONNECT_TARGET
EOF

# Certificado (Auto-regeneración)
echo -e "${YELLOW}[+] Generando certificado SSL Premium...${NC}"
openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -sha256 -subj "/CN=MaximusVpsMx/O=Maximus/C=US" -keyout /etc/stunnel/stunnel.pem -out /etc/stunnel/stunnel.pem >/dev/null 2>&1

# Habilitar y Reiniciar
sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4 2>/dev/null
ufw allow $SSL_PORT/tcp 2>/dev/null

systemctl daemon-reload
systemctl enable stunnel4 > /dev/null 2>&1
systemctl restart stunnel4 > /dev/null 2>&1

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN} ✅ STUNNEL v4.0 CONFIGURADO EXITOSAMENTE${NC}"
echo -e "${CYAN} Puerto SSL: $SSL_PORT${NC}"
echo -e "${CYAN} Modo:       $( [ "$mode_opt" == "3" ] && echo "HÍBRIDO" || ( [ "$mode_opt" == "1" ] && echo "DIRECTO" || echo "PROXY" ) )${NC}"
echo -e "${GREEN}=======================================================${NC}"
sleep 2
