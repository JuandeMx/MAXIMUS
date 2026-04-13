#!/bin/bash
# MaximusVpsMx - Instalador Avanzado Stunnel4 (SSL)
# Soporta Modo Directo y Modo Cadena (Proxy)

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

clear
echo -e "${CYAN}=======================================================${NC}"
echo -e "${YELLOW}           CONFIGURACIÓN DE STUNNEL (SSL)${NC}"
echo -e "${CYAN}=======================================================${NC}"
echo -e "${WHITE} Elige el modo de funcionamiento para el SSL:${NC}"
echo -e "${RED}-------------------------------------------------------${NC}"
echo -e " [1] MODO DIRECTO (SSL → SSH)"
echo -e "     ${YELLOW}* Recomendado para velocidad (Sin Payload).${NC}"
echo -e " [2] MODO CADENA (SSL → PROXY → SSH)"
echo -e "     ${YELLOW}* Permite usar Payloads/Websockets en la App.${NC}"
echo -e "${RED}-------------------------------------------------------${NC}"
read -p " Selecciona una opción [1-2]: " mode_opt

# --- VARIABLES POR DEFECTO ---
SSL_PORT=443
BACKEND_PORT=22

case $mode_opt in
    1)
        # MODO DIRECTO
        echo -e "\n${CYAN}▶ MODO DIRECTO SELECCIONADO${NC}"
        read -p " Puerto SSL a escuchar (ej: 443, 444): " SSL_PORT
        [ -z "$SSL_PORT" ] && SSL_PORT=443

        echo -e "\n${WHITE} Configuración del puerto destino (Backend):${NC}"
        echo -e " [1] Autodetectar (OpenSSH/Dropbear)"
        echo -e " [2] Configuración Manual"
        read -p " Elige: " back_opt
        
        if [ "$back_opt" == "1" ]; then
            echo -e "${YELLOW}[+] Detectando servicios...${NC}"
            if systemctl is-active --quiet dropbear; then
                # Intentar leer puerto de dropbear
                BACKEND_PORT=$(grep "DROPBEAR_PORT=" /etc/default/dropbear | cut -d= -f2 | tr -d '"')
                [ -z "$BACKEND_PORT" ] && BACKEND_PORT=44
                echo -e "${GREEN}✓ Dropbear detectado en puerto $BACKEND_PORT${NC}"
            elif systemctl is-active --quiet ssh; then
                BACKEND_PORT=22
                echo -e "${GREEN}✓ OpenSSH detectado en puerto 22${NC}"
            else
                echo -e "${RED}✗ No se detectaron servicios SSH activos. Usando puerto 22 por defecto.${NC}"
                BACKEND_PORT=22
            fi
        else
            read -p " Ingresa puerto local destino (ej: 22, 44): " BACKEND_PORT
            [ -z "$BACKEND_PORT" ] && BACKEND_PORT=22
        fi
        
        CONNECT_TARGET="127.0.0.1:$BACKEND_PORT"
        ;;
    2)
        # MODO CADENA
        echo -e "\n${CYAN}▶ MODO CADENA (PROXY) SELECCIONADO${NC}"
        read -p " Puerto SSL a escuchar (ej: 443, 444): " SSL_PORT
        [ -z "$SSL_PORT" ] && SSL_PORT=443
        
        echo -e "${YELLOW}[+] Verificando Proxy Python en puerto 80...${NC}"
        if ! systemctl is-active --quiet mx-proxy; then
            echo -e "${YELLOW}    → El Proxy no está activo. Levantándolo en puerto 80 automáticamente...${NC}"
            bash /etc/MaximusVpsMx/modules/install_mx-proxy.sh 80 > /dev/null 2>&1
        fi
        
        CONNECT_TARGET="127.0.0.1:80"
        echo -e "${GREEN}✓ Conectando Stunnel al Proxy (Puerto 80)${NC}"
        ;;
    *)
        echo -e "${RED}Opción inválida.${NC}"
        exit 1
        ;;
esac

# --- INSTALACIÓN Y CONFIGURACIÓN ---
echo -e "\n${YELLOW}[+] Aplicando configuración de Stunnel de Alta Compatibilidad...${NC}"
apt-get install stunnel4 -y > /dev/null 2>&1

# Asegurar directorio de logs
mkdir -p /var/log/stunnel4
chown stunnel4:stunnel4 /var/log/stunnel4

cat > /etc/stunnel/stunnel.conf << EOF
cert = /etc/stunnel/stunnel.pem
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1
socket = l:SO_KEEPALIVE=1
socket = r:SO_KEEPALIVE=1
TIMEOUTclose = 0
TIMEOUTconnect = 10
TIMEOUTidle = 600

# Parámetros de Compatibilidad para Apps Móviles
sslVersion = all
options = NO_SSLv2
options = NO_SSLv3
ciphers = HIGH:!aNULL:!MD5

# Debug (Activar si hay problemas)
debug = 7
output = /var/log/stunnel4/stunnel.log

[ssh]
client = no
accept = $SSL_PORT
connect = $CONNECT_TARGET
EOF

# Certificado
if [ ! -f /etc/stunnel/stunnel.pem ]; then
    echo -e "${YELLOW}[+] Generando certificado SSL...${NC}"
    openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -sha256 -subj "/CN=MaximusVpsMx/O=Maximus/C=US" -keyout /etc/stunnel/stunnel.pem -out /etc/stunnel/stunnel.pem >/dev/null 2>&1
fi

sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4 2>/dev/null
ufw allow $SSL_PORT/tcp 2>/dev/null

echo -e "${YELLOW}[+] Reiniciando servicios...${NC}"
systemctl daemon-reload
systemctl enable stunnel4 > /dev/null 2>&1
systemctl restart stunnel4 > /dev/null 2>&1

echo -e "\n${GREEN}=======================================================${NC}"
echo -e "${GREEN} ✅ STUNNEL CONFIGURADO EXITOSAMENTE${NC}"
echo -e "${CYAN} Puerto SSL: $SSL_PORT${NC}"
echo -e "${CYAN} Destino:    $CONNECT_TARGET${NC}"
echo -e "${GREEN}=======================================================${NC}"
sleep 2
