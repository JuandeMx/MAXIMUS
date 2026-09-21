#!/bin/bash
# MaximusVpsMx - HCR Server (HTTP Custom Relay) Manager
# Axolot Supremacy Edition

RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
NC='\033[0m'

HCR_DIR="/etc/MaximusVpsMx/hcr"
HCR_BIN="/usr/local/bin/hcr-server"
HCR_SERVICE="/etc/systemd/system/hcr-server.service"
CONF_PORT="$HCR_DIR/port.conf"
CONF_TRANS="$HCR_DIR/transport.conf"

ui_hr() { echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"; }
ui_subhr() { echo -e "${CYAN}───────────────────────────────────────────────────────${NC}"; }
ui_prompt() { echo -ne "${YELLOW}$1${NC}"; }
ui_pause() { echo ""; read -p "Presiona Enter para continuar..." ; }
ui_header() {
    clear
    ui_hr
    echo -e "${YELLOW}         GESTOR HCR SERVER (HTTP CUSTOM RELAY)${NC}"
    ui_hr
}

# Obtener IP pública
get_ip() {
    local ip=$(curl -4 -sL --max-time 3 ipv4.icanhazip.com 2>/dev/null)
    [ -z "$ip" ] && ip=$(curl -4 -sL --max-time 3 ifconfig.me 2>/dev/null)
    [ -z "$ip" ] && ip="TU_IP"
    echo "$ip"
}

# Obtener puerto local SSH
get_ssh_port() {
    local p=$(grep -E "^Port " /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' | head -1)
    [ -z "$p" ] && p=22
    echo "$p"
}

# Verificar o instalar binario
install_binary() {
    mkdir -p "$HCR_DIR"
    mkdir -p "/var/log/MaximusVpsMx"
    
    if [ -f "/etc/MaximusVpsMx/bin/hcr-server-linux-amd64" ]; then
        echo -e "${GREEN}[✔] Copiando binario HCR desde Bóveda Local Maximus...${NC}"
        cp -f "/etc/MaximusVpsMx/bin/hcr-server-linux-amd64" "$HCR_BIN"
    elif [ -f "./bin/hcr-server-linux-amd64" ]; then
        echo -e "${GREEN}[✔] Copiando binario HCR desde carpeta local...${NC}"
        cp -f "./bin/hcr-server-linux-amd64" "$HCR_BIN"
    else
        echo -e "${YELLOW}[+] Descargando binario HCR desde Bóveda Remota Maximus...${NC}"
        if curl -sL -f --connect-timeout 10 --max-time 60 -o "$HCR_BIN" "https://raw.githubusercontent.com/JuandeMx/MAXIMUS/main/bin/hcr-server-linux-amd64"; then
            echo -e "${GREEN}[✔] Descarga exitosa desde GitHub MAXIMUS.${NC}"
        else
            echo -e "${YELLOW}[!] Mirror alternativo Lacasita...${NC}"
            curl -sL -f --connect-timeout 10 --max-time 60 -o "$HCR_BIN" "https://raw.githubusercontent.com/lacasitamx/SCRIPTMOD-LACASITA/master/hcr-server"
        fi
    fi

    if [ ! -f "$HCR_BIN" ] || [ "$(stat -c%s "$HCR_BIN" 2>/dev/null || echo 0)" -lt 500000 ]; then
        echo -e "${RED}❌ Error: No se pudo obtener el binario de HCR Server.${NC}"
        return 1
    fi

    chmod 755 "$HCR_BIN"
    return 0
}

# Configurar certificados SSL
setup_ssl() {
    local cert_file="$HCR_DIR/fullchain.pem"
    local key_file="$HCR_DIR/privkey.pem"

    if [ -f "$cert_file" ] && [ -f "$key_file" ]; then
        return 0
    fi

    echo -e "${YELLOW}[+] Generando certificados SSL para modo seguro (TLS)...${NC}"
    # Si stunnel ya tiene certificado, podemos reusarlo o generar uno nuevo
    if [ -f "/etc/stunnel/stunnel.pem" ]; then
        cp -f "/etc/stunnel/stunnel.pem" "$cert_file"
        cp -f "/etc/stunnel/stunnel.pem" "$key_file"
    else
        openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
            -keyout "$key_file" \
            -out "$cert_file" \
            -subj "/CN=maximus-hcr/O=MaximusVpsMx/C=MX" >/dev/null 2>&1
    fi
    chmod 600 "$key_file" 2>/dev/null
    chmod 644 "$cert_file" 2>/dev/null
}

instalar_hcr() {
    ui_header
    echo -e "${WHITE}  CONFIGURACIÓN E INSTALACIÓN DE HCR SERVER${NC}"
    ui_subhr

    if ! install_binary; then
        ui_pause
        return
    fi

    # 1. Puerto
    local old_port="8888"
    [ -f "$CONF_PORT" ] && old_port=$(cat "$CONF_PORT")
    echo -e " ${CYAN}Puerto de escucha para HCR Server${NC} (Default: ${GREEN}${old_port}${NC}):"
    ui_prompt " > Puerto: " ; read n_port
    [ -z "$n_port" ] && n_port="$old_port"

    if ! [[ "$n_port" =~ ^[0-9]+$ ]] || [ "$n_port" -lt 1 ] || [ "$n_port" -gt 65535 ]; then
        echo -e "${RED}❌ Puerto inválido. Se usará 8888.${NC}"
        n_port="8888"
    fi

    # 2. Modo de transporte
    local old_trans="auto"
    [ -f "$CONF_TRANS" ] && old_trans=$(cat "$CONF_TRANS")
    echo -e "\n ${CYAN}Modo de Transporte [tls | plain | auto]${NC} (Default: ${GREEN}${old_trans}${NC}):"
    echo -e "   ${WHITE}auto${NC}  : Acepta conexiones con TLS (HTTPS/SNI) y Directas (Recomendado)"
    echo -e "   ${WHITE}tls${NC}   : Únicamente conexiones cifradas con TLS/SSL"
    echo -e "   ${WHITE}plain${NC} : Únicamente conexiones en texto plano (sin TLS)"
    ui_prompt " > Modo: " ; read n_trans
    [ -z "$n_trans" ] && n_trans="$old_trans"
    case "$n_trans" in
        tls|plain|auto) ;;
        *) n_trans="auto" ;;
    esac

    # 3. Buffer y timeouts
    echo -e "\n ${CYAN}MAX_DOWNLOAD_FRAME${NC} (Default: ${GREEN}6144${NC}):"
    ui_prompt " > Frame: " ; read n_frame
    [ -z "$n_frame" ] && n_frame="6144"

    echo -e "\n ${CYAN}DOWNLOAD_POLL_TIMEOUT${NC} (Default: ${GREEN}8s${NC}):"
    ui_prompt " > Timeout: " ; read n_timeout
    [ -z "$n_timeout" ] && n_timeout="8s"

    local ssh_port=$(get_ssh_port)

    # Detener previo si existe
    systemctl stop hcr-server 2>/dev/null

    # Certificados si aplica
    local tls_flags=""
    if [ "$n_trans" = "tls" ] || [ "$n_trans" = "auto" ]; then
        setup_ssl
        tls_flags=" --tls-cert $HCR_DIR/fullchain.pem --tls-key $HCR_DIR/privkey.pem"
    fi

    # Crear servicio systemd
    echo -e "\n${YELLOW}[+] Configurando servicio Systemd (hcr-server.service)...${NC}"
    cat > "$HCR_SERVICE" << EOF
[Unit]
Description=MaximusVpsMx HCR Relay Service (HTTP Custom)
After=network.target ssh.service sshd.service
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$HCR_DIR
ExecStart=$HCR_BIN --listen :${n_port} --target 127.0.0.1:${ssh_port} --transport ${n_trans}${tls_flags} --max-download-frame ${n_frame} --download-poll-timeout ${n_timeout}
Restart=always
RestartSec=3s
LimitNOFILE=65535
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hcr-server

[Install]
WantedBy=multi-user.target
EOF

    # Guardar configuración
    echo "$n_port" > "$CONF_PORT"
    echo "$n_trans" > "$CONF_TRANS"

    # Abrir puerto en firewall
    ufw allow "$n_port/tcp" >/dev/null 2>&1

    # Iniciar servicio
    systemctl daemon-reload
    systemctl enable hcr-server >/dev/null 2>&1
    systemctl restart hcr-server

    sleep 2
    if systemctl is-active --quiet hcr-server; then
        local ip_serv=$(get_ip)
        ui_hr
        echo -e "${GREEN}  ✅ HCR SERVER INSTALADO Y ACTIVADO CON ÉXITO${NC}"
        ui_subhr
        echo -e " ${CYAN}IP del Servidor :${WHITE} $ip_serv${NC}"
        echo -e " ${CYAN}Puerto HCR      :${WHITE} $n_port${NC}"
        echo -e " ${CYAN}Modo Transporte :${WHITE} $n_trans${NC}"
        echo -e " ${CYAN}Destino Local   :${WHITE} 127.0.0.1:$ssh_port (SSH)${NC}"
        ui_subhr
        echo -e "${YELLOW}  📱 CONFIGURACIÓN EN HTTP CUSTOM:${NC}"
        echo -e "  1. En HTTP Custom, activa el módulo o perfil HCR."
        echo -e "  2. Servidor: ${WHITE}$ip_serv:$n_port${NC}"
        echo -e "  3. Autenticación: Usa cualquier usuario SSH creado en Maximus."
        ui_hr
    else
        echo -e "${RED}❌ Error al iniciar el servicio HCR Server.${NC}"
        echo -e "${YELLOW}Revisa los registros con: journalctl -u hcr-server -e${NC}"
    fi
    ui_pause
}

detener_iniciar_hcr() {
    ui_header
    if systemctl is-active --quiet hcr-server; then
        echo -e "${YELLOW}[+] Deteniendo HCR Server...${NC}"
        systemctl stop hcr-server
        echo -e "${GREEN}✅ Servicio detenido.${NC}"
    else
        echo -e "${YELLOW}[+] Iniciando HCR Server...${NC}"
        systemctl start hcr-server
        sleep 1
        if systemctl is-active --quiet hcr-server; then
            echo -e "${GREEN}✅ Servicio iniciado con éxito.${NC}"
        else
            echo -e "${RED}❌ Falló al iniciar. Revisa los logs.${NC}"
        fi
    fi
    ui_pause
}

reiniciar_hcr() {
    ui_header
    echo -e "${YELLOW}[+] Reiniciando HCR Server...${NC}"
    systemctl restart hcr-server
    sleep 1
    if systemctl is-active --quiet hcr-server; then
        echo -e "${GREEN}✅ Servicio reiniciado correctamente.${NC}"
    else
        echo -e "${RED}❌ Falló al reiniciar.${NC}"
    fi
    ui_pause
}

ver_logs_hcr() {
    ui_header
    echo -e "${YELLOW}▶ Mostrando logs en vivo (Presiona Ctrl+C para salir)...${NC}"
    ui_subhr
    journalctl -u hcr-server -n 40 -f
}

desinstalar_hcr() {
    ui_header
    echo -e "${RED}  ⚠️ DESINSTALAR HCR SERVER${NC}"
    ui_subhr
    read -p "¿Estás seguro de eliminar HCR Server por completo? (s/n): " c_del
    if [[ "$c_del" == "s" || "$c_del" == "S" ]]; then
        echo -e "\n${YELLOW}[+] Deteniendo y limpiando HCR Server...${NC}"
        systemctl stop hcr-server 2>/dev/null
        systemctl disable hcr-server 2>/dev/null
        
        if [ -f "$CONF_PORT" ]; then
            local p_del=$(cat "$CONF_PORT")
            [ -n "$p_del" ] && ufw delete allow "$p_del/tcp" >/dev/null 2>&1
        fi
        
        rm -f "$HCR_SERVICE" 2>/dev/null
        rm -f "$HCR_BIN" 2>/dev/null
        rm -rf "$HCR_DIR" 2>/dev/null
        systemctl daemon-reload
        echo -e "${GREEN}✅ HCR Server desinstalado completamente.${NC}"
    else
        echo -e "${CYAN}Operación cancelada.${NC}"
    fi
    ui_pause
}

# --- BUCLE PRINCIPAL DEL GESTOR ---
while true; do
    ui_header
    
    if systemctl is-active --quiet hcr-server 2>/dev/null; then
        port_act="--"
        [ -f "$CONF_PORT" ] && port_act=$(cat "$CONF_PORT")
        trans_act="auto"
        [ -f "$CONF_TRANS" ] && trans_act=$(cat "$CONF_TRANS")
        st="${GREEN}[ ACTIVO : Puerto $port_act | Modo $trans_act ]${NC}"
    else
        st="${RED}[ INACTIVO / APAGADO ]${NC}"
    fi

    echo -e " Estado: $st"
    ui_subhr
    echo -e "  ${CYAN}[1] >${WHITE} Instalar / Reconfigurar HCR Server${NC}"
    echo -e "  ${CYAN}[2] >${WHITE} Iniciar / Detener HCR Server${NC}"
    echo -e "  ${CYAN}[3] >${WHITE} Reiniciar HCR Server${NC}"
    echo -e "  ${CYAN}[4] >${WHITE} Ver Logs en Vivo (Monitoreo)${NC}"
    echo -e "  ${CYAN}[5] >${RED} Desinstalar HCR Server${NC}"
    ui_hr
    echo -e "  ${WHITE}[0] > VOLVER AL MENÚ DE PROTOCOLOS${NC}"
    ui_hr
    ui_prompt " Selecciona una opción: " ; read opt_hcr

    case $opt_hcr in
        1) instalar_hcr ;;
        2) detener_iniciar_hcr ;;
        3) reiniciar_hcr ;;
        4) ver_logs_hcr ;;
        5) desinstalar_hcr ;;
        0) break ;;
        *) continue ;;
    esac
done
