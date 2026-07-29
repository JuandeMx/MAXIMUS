#!/bin/bash
# MaximusVpsMx - Native 3X-UI Replica Inbound & Client Manager (100% Terminal)
# Réplica Exacta de X-UI (Inbounds + Protocolos + Transmisiones + Seguridad + Clientes)

RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
MAGENTA='\033[1;35m'
NC='\033[0m'

V2RAY_DIR="/etc/MaximusVpsMx/v2ray"
V2RAY_CONF="$V2RAY_DIR/config.json"
V2RAY_DB="/etc/MaximusVpsMx/v2ray_inbounds.db"
V2RAY_CLIENTS_DB="/etc/MaximusVpsMx/v2ray_clients.db"
XRAY_BIN="/usr/local/bin/xray"

mkdir -p "$V2RAY_DIR"
touch "$V2RAY_DB"
touch "$V2RAY_CLIENTS_DB"

ui_hr() { echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"; }
ui_subhr() { echo -e "${CYAN}───────────────────────────────────────────────────────${NC}"; }
ui_pause() { echo "" ; read -p "Presiona Enter para continuar..." ; }

check_xray_installed() {
    if [ -x "$XRAY_BIN" ]; then
        return 0
    else
        return 1
    fi
}

install_xray_core() {
    echo -e "${CYAN}[+] Instalando dependencias (jq, qrencode, unzip, curl, openssl)...${NC}"
    apt-get update -y >/dev/null 2>&1
    apt-get install -y jq qrencode unzip curl openssl >/dev/null 2>&1

    echo -e "${CYAN}[+] Descargando última versión de Xray-core...${NC}"
    arch=$(uname -m)
    case "$arch" in
        x86_64) xray_arch="64" ;;
        aarch64|arm64) xray_arch="arm64-v8a" ;;
        armv7l) xray_arch="arm32-v7a" ;;
        *) xray_arch="64" ;;
    esac

    mkdir -p /tmp/xray_install
    url="https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-${xray_arch}.zip"
    if curl -sL "$url" -o /tmp/xray_install/xray.zip; then
        unzip -o /tmp/xray_install/xray.zip -d /tmp/xray_install/ >/dev/null 2>&1
        cp -f /tmp/xray_install/xray "$XRAY_BIN"
        chmod +x "$XRAY_BIN"
        rm -rf /tmp/xray_install
        echo -e "${GREEN}✅ Xray-core instalado exitosamente en $XRAY_BIN.${NC}"
    else
        echo -e "${RED}❌ Error al descargar Xray-core. Revisa tu conexión internet.${NC}"
        return 1
    fi

    create_v2ray_systemd
    init_v2ray_config
}

create_v2ray_systemd() {
    cat << 'EOF' > /etc/systemd/system/maximus-v2ray.service
[Unit]
Description=Maximus Native V2Ray Xray Service
After=network.target nss-lookup.target

[Service]
User=root
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /etc/MaximusVpsMx/v2ray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable maximus-v2ray >/dev/null 2>&1
}

init_v2ray_config() {
    if [ ! -f "$V2RAY_CONF" ] || [ ! -s "$V2RAY_CONF" ]; then
        cat << 'EOF' > "$V2RAY_CONF"
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "block"
    }
  ]
}
EOF
    fi
}

reload_v2ray_service() {
    systemctl restart maximus-v2ray >/dev/null 2>&1
}

# ==============================================================================
# PASO 1: CREAR Y CONFIGURAR MÉTODOS (INBOUND BUILDER REPLICA 3X-UI)
# ==============================================================================
add_inbound_wizard() {
    if ! check_xray_installed; then
        echo -e "${RED}❌ Xray-core no está instalado. Ejecuta la Opción 1 primero.${NC}"
        ui_pause
        return
    fi

    clear
    ui_hr
    echo -e "${YELLOW}       AGREGAR NUEVO INBOUND / MÉTODO (RÉPLICA 3X-UI)${NC}"
    ui_hr

    # 1. Remark / Nombre del Método
    read -p " 1. Remark / Nombre del Método (ej. Telcel Trick WS): " remark
    [ -z "$remark" ] && remark="Inbound-$(date +%s)"

    # 2. Protocolo
    echo -e "\n ${CYAN}2. Selecciona el Protocolo:${NC}"
    echo -e "  [1] vless         [2] vmess         [3] trojan"
    echo -e "  [4] shadowsocks   [5] dokodemo-door [6] socks"
    echo -e "  [7] http          [8] wireguard     [9] tun"
    read -p " Selecciona [1-9] (Default: 1): " p_choice
    case "$p_choice" in
        2) proto="vmess" ;;
        3) proto="trojan" ;;
        4) proto="shadowsocks" ;;
        5) proto="dokodemo-door" ;;
        6) proto="socks" ;;
        7) proto="http" ;;
        8) proto="wireguard" ;;
        9) proto="tun" ;;
        *) proto="vless" ;;
    esac

    # 3. Listen IP y Puerto
    read -p " 3. IP de Escucha / Listen IP [Default: 0.0.0.0]: " listen_ip
    [ -z "$listen_ip" ] && listen_ip="0.0.0.0"

    read -p " 4. Puerto de Escucha / Port (ej. 20562, 8080, 443): " port
    while [[ -z "$port" || ! "$port" =~ ^[0-9]+$ ]]; do
        read -p " ⚠️ Ingrese un puerto válido (1-65535): " port
    done

    # 5. Transmission / Transporte
    echo -e "\n ${CYAN}5. Tipo de Transmisión (Network / Transmission):${NC}"
    echo -e "  [1] TCP (RAW)"
    echo -e "  [2] mKCP"
    echo -e "  [3] WebSocket (WS)"
    echo -e "  [4] gRPC"
    echo -e "  [5] HttpUpgrade"
    echo -e "  [6] XHTTP"
    read -p " Selecciona [1-6] (Default: 3 WS): " net_choice

    path="/"
    host_header=""
    service_name=""
    case "$net_choice" in
        1) net="tcp" ;;
        2) net="kcp" ;;
        4) net="grpc"
           read -p "   - gRPC ServiceName [Default: grpc-service]: " service_name
           [ -z "$service_name" ] && service_name="grpc-service"
           ;;
        5) net="httpupgrade"
           read -p "   - HttpUpgrade Path [Default: /httpupgrade]: " path
           [ -z "$path" ] && path="/httpupgrade"
           read -p "   - Host Header / Trick (Opcional): " host_header
           ;;
        6) net="xhttp"
           read -p "   - XHTTP Path [Default: /xhttp]: " path
           [ -z "$path" ] && path="/xhttp"
           read -p "   - Host Header / Trick (Opcional): " host_header
           ;;
        *) net="ws"
           read -p "   - WebSocket Path [Default: /ws]: " path
           [ -z "$path" ] && path="/ws"
           read -p "   - Host Header / Trick (Opcional, ej. migracion.telcel.com): " host_header
           ;;
    esac

    # 6. Security (None, TLS, REALITY)
    echo -e "\n ${CYAN}6. Capa de Seguridad (Security):${NC}"
    echo -e "  [1] None (Sin cifrado / Directo)"
    echo -e "  [2] TLS (Certificado SSL)"
    echo -e "  [3] REALITY (Post-Quantum / Destino Camuflado)"
    read -p " Selecciona [1-3] (Default: 1 None): " sec_choice

    sec="none"
    sni=""
    fp="chrome"
    alpn="h2,http/1.1"
    pub_cert=""
    priv_key=""
    reality_dest=""
    reality_priv=""
    reality_pub=""
    reality_short=""

    case "$sec_choice" in
        2) sec="tls"
           read -p "   - Server Name Indication (SNI) [ej. midominio.com]: " sni
           read -p "   - Impostación uTLS [chrome/firefox/safari/randomised] (Default: chrome): " fp
           [ -z "$fp" ] && fp="chrome"
           read -p "   - Ruta Certificado Público [Default: /etc/dropbear/banner o /etc/x-ui/server.crt]: " pub_cert
           read -p "   - Ruta Llave Privada [Default: /etc/x-ui/server.key]: " priv_key
           ;;
        3) sec="reality"
           read -p "   - Target / Destino Camuflado [Default: www.google.com:443]: " reality_dest
           [ -z "$reality_dest" ] && reality_dest="www.google.com:443"
           read -p "   - SNI Camuflado [Default: www.google.com]: " sni
           [ -z "$sni" ] && sni="www.google.com"

           # Generar claves REALITY automáticamente con Xray
           keys_out=$("$XRAY_BIN" x25519 2>/dev/null)
           reality_priv=$(echo "$keys_out" | grep -i "Private key" | awk '{print $NF}')
           reality_pub=$(echo "$keys_out" | grep -i "Public key" | awk '{print $NF}')
           [ -z "$reality_priv" ] && reality_priv=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 43)
           reality_short=$(openssl rand -hex 8)
           echo -e "   ${GREEN}[+] Claves REALITY generadas automáticamente.${NC}"
           echo -e "       Private Key : $reality_priv"
           echo -e "       Public Key  : $reality_pub"
           echo -e "       Short ID    : $reality_short"
           ;;
        *) sec="none" ;;
    esac

    # 7. Toggles (Sniffing, PROXY Protocol)
    read -p "\n 7. ¿Activar Sniffing (Detección HTTP/TLS/QUIC)? [S/N] (Default: S): " act_sniff
    [[ "$act_sniff" =~ ^[Nn]$ ]] && enable_sniff=false || enable_sniff=true

    # Construir Inbound JSON en Xray config.json
    tag_id="inbound-$port-$proto"
    
    inbound_json=$(cat <<EOF
{
  "tag": "$tag_id",
  "port": $port,
  "listen": "$listen_ip",
  "protocol": "$proto",
  "settings": {
    "clients": [],
    "decryption": "none"
  },
  "streamSettings": {
    "network": "$net",
    "security": "$sec"
  },
  "sniffing": {
    "enabled": $enable_sniff,
    "destOverride": ["http", "tls", "quic"]
  }
}
EOF
)

    # Inyectar sub-propiedades WS / gRPC / TLS / REALITY al JSON
    tmp_file="/tmp/inbound_building.json"
    echo "$inbound_json" > "$tmp_file"

    if [ "$net" == "ws" ]; then
        tmp_json=$(jq --arg path "$path" --arg host "$host_header" '.streamSettings.wsSettings = {"path": $path, "headers": {"Host": $host}}' "$tmp_file")
        echo "$tmp_json" > "$tmp_file"
    elif [ "$net" == "grpc" ]; then
        tmp_json=$(jq --arg sname "$service_name" '.streamSettings.grpcSettings = {"serviceName": $sname}' "$tmp_file")
        echo "$tmp_json" > "$tmp_file"
    elif [ "$net" == "httpupgrade" ]; then
        tmp_json=$(jq --arg path "$path" --arg host "$host_header" '.streamSettings.httpupgradeSettings = {"path": $path, "host": $host}' "$tmp_file")
        echo "$tmp_json" > "$tmp_file"
    fi

    if [ "$sec" == "tls" ]; then
        tmp_json=$(jq --arg sni "$sni" --arg cert "$pub_cert" --arg key "$priv_key" '.streamSettings.tlsSettings = {"serverName": $sni, "certificates": [{"certificateFile": $cert, "keyFile": $key}]}' "$tmp_file")
        echo "$tmp_json" > "$tmp_file"
    elif [ "$sec" == "reality" ]; then
        tmp_json=$(jq --arg dest "$reality_dest" --arg sni "$sni" --arg priv "$reality_priv" --arg sid "$reality_short" '.streamSettings.realitySettings = {"show": false, "dest": $dest, "xver": 0, "serverNames": [$sni], "privateKey": $priv, "shortIds": [$sid]}' "$tmp_file")
        echo "$tmp_json" > "$tmp_file"
    fi

    # Agregar nuevo inbound al config.json de Xray
    final_inbound=$(cat "$tmp_file")
    rm -f "$tmp_file"

    updated_config=$(jq --argjson new_in "$final_inbound" '.inbounds += [$new_in]' "$V2RAY_CONF")
    echo "$updated_config" > "$V2RAY_CONF"

    # Guardar Metadata en la Base de Datos local de Inbounds
    # Registro: id|remark|proto|port|net|sec|path|host|sni|pubkey
    echo "$tag_id|$remark|$proto|$port|$net|$sec|$path|$host_header|$sni|$reality_pub" >> "$V2RAY_DB"

    reload_v2ray_service

    clear
    ui_hr
    echo -e "${GREEN}       ✅ INBOUND / MÉTODO CREADO EXITOSAMENTE (3X-UI REPLICA)${NC}"
    ui_hr
    echo -e "${CYAN} TAG / ID          :${WHITE} $tag_id${NC}"
    echo -e "${CYAN} REMARK / NOMBRE   :${WHITE} $remark${NC}"
    echo -e "${CYAN} PROTOCOLO         :${WHITE} $proto${NC}"
    echo -e "${CYAN} PUERTO DE ESCUCHA :${WHITE} $port${NC}"
    echo -e "${CYAN} TRANSMISIÓN (NET) :${WHITE} $net (Path: $path | Host: $host_header)${NC}"
    echo -e "${CYAN} SEGURIDAD         :${WHITE} $sec (SNI: $sni)${NC}"
    [ -n "$reality_pub" ] && echo -e "${CYAN} REALITY PUBLIC KEY:${WHITE} $reality_pub${NC}"
    ui_hr
    ui_pause
}

list_inbounds() {
    ui_hr
    echo -e "${YELLOW}           MÉTODOS / INBOUNDS REGISTRADOS (3X-UI)${NC}"
    ui_hr
    if [ ! -s "$V2RAY_DB" ]; then
        echo -e " ${RED}No hay inbounds o métodos registrados.${NC}"
    else
        printf "${WHITE}%-20s | %-8s | %-6s | %-8s | %-8s${NC}\n" "REMARK / MODO" "PROTO" "PORT" "NET" "SECURITY"
        ui_subhr
        while IFS='|' read -r tid rm pr po ne se pa ho sn pb; do
            [ -z "$tid" ] && continue
            printf " ${CYAN}%-20s${NC} | %-8s | %-6s | %-8s | %-8s\n" "$rm" "$pr" "$po" "$ne" "$se"
        done < "$V2RAY_DB"
    fi
    ui_hr
}

# ==============================================================================
# PASO 2: ASIGNACIÓN Y CREACIÓN DE CLIENTES EN UN INBOUND
# ==============================================================================
create_client_wizard() {
    if [ ! -s "$V2RAY_DB" ]; then
        echo -e "${RED}❌ No hay métodos/inbounds creados. Registra un Método primero (Opción 2).${NC}"
        ui_pause
        return
    fi

    clear
    ui_hr
    echo -e "${YELLOW}             CREAR CLIENTE V2RAY ASIGNANDO MÉTODO${NC}"
    ui_hr
    
    # Mostrar Inbounds disponibles
    list_inbounds
    echo ""
    read -p " Selecciona el Número o Nombre del Método Inbound: " sel_inbound
    [ -z "$sel_inbound" ] && return

    # Buscar Inbound en DB
    inbound_line=$(grep -i "$sel_inbound" "$V2RAY_DB" | head -n 1)
    if [ -z "$inbound_line" ]; then
        echo -e "${RED}❌ Método no encontrado.${NC}"
        ui_pause
        return
    fi

    IFS='|' read -r tid remark proto port net sec path host_header sni reality_pub <<< "$inbound_line"

    read -p " Nombre del Cliente (ej. Juan): " client_name
    [ -z "$client_name" ] && return

    read -p " Días de validez [Default: 30]: " dias
    [ -z "$dias" ] && dias=30
    exp_date=$(date -d "+$dias days" +%Y-%m-%d)

    uuid=$(cat /proc/sys/kernel/random/uuid)

    # Agregar cliente al JSON de Xray según el Tag Inbound y Protocolo
    if [ "$proto" == "trojan" ] || [ "$proto" == "shadowsocks" ]; then
        # Para Trojan / Shadowsocks se usa password
        tmp_json=$(jq --arg tag "$tid" --arg pass "$uuid" --arg email "$client_name" \
            '(.inbounds[] | select(.tag == $tag).settings.clients) += [{"password": $pass, "email": $email}]' "$V2RAY_CONF")
    else
        # Para VLESS / VMESS se usa UUID
        tmp_json=$(jq --arg tag "$tid" --arg id "$uuid" --arg email "$client_name" \
            '(.inbounds[] | select(.tag == $tag).settings.clients) += [{"id": $id, "alterId": 0, "email": $email}]' "$V2RAY_CONF")
    fi

    echo "$tmp_json" > "$V2RAY_CONF"
    
    # Guardar en Base de Datos de Clientes
    echo "$client_name|$uuid|$tid|$exp_date" >> "$V2RAY_CLIENTS_DB"
    reload_v2ray_service

    # Generar URI Link de conexión
    ip=$(curl -s4 ifconfig.me || echo "127.0.0.1")
    domain=""
    [ -f /etc/MaximusVpsMx/domain.conf ] && domain=$(cat /etc/MaximusVpsMx/domain.conf)
    [ -z "$domain" ] && domain="$ip"

    add_host="$domain"
    [ -n "$host_header" ] && add_host="$host_header"

    if [ "$proto" == "vmess" ]; then
        v_json=$(cat <<EOF
{
  "v": "2",
  "ps": "$client_name-$remark",
  "add": "$domain",
  "port": "$port",
  "id": "$uuid",
  "aid": "0",
  "scy": "auto",
  "net": "$net",
  "type": "none",
  "host": "$host_header",
  "path": "$path",
  "tls": "$sec"
}
EOF
)
        b64_uri=$(echo -n "$v_json" | base64 -w 0)
        final_link="vmess://$b64_uri"
    elif [ "$proto" == "vless" ]; then
        if [ "$sec" == "reality" ]; then
            final_link="vless://$uuid@$domain:$port?type=$net&security=reality&pbk=$reality_pub&fp=chrome&sni=$sni&path=$path#$client_name-$remark"
        else
            final_link="vless://$uuid@$domain:$port?type=$net&security=$sec&host=$host_header&path=$path#$client_name-$remark"
        fi
    elif [ "$proto" == "trojan" ]; then
        final_link="trojan://$uuid@$domain:$port?type=$net&security=$sec&host=$host_header&path=$path#$client_name-$remark"
    else
        final_link="$proto://$uuid@$domain:$port#$client_name-$remark"
    fi

    clear
    ui_hr
    echo -e "${GREEN}       ✅ CLIENTE '$client_name' GENERADO CON ÉXITO${NC}"
    ui_hr
    echo -e "${CYAN} CLIENTE   :${WHITE} $client_name${NC}"
    echo -e "${CYAN} MÉTODO    :${WHITE} $remark (Protocolo $proto | Puerto $port)${NC}"
    echo -e "${CYAN} UUID / KEY:${WHITE} $uuid${NC}"
    echo -e "${CYAN} EXPIRACIÓN:${WHITE} $exp_date ($dias Días)${NC}"
    ui_subhr
    echo -e "${YELLOW} ENLACE DE CONEXIÓN GENERADO (URL):${NC}"
    echo -e "${WHITE}$final_link${NC}"
    ui_subhr
    echo -e "${YELLOW} CÓDIGO QR PARA ESCANEAR EN APP (v2rayNG / HTTP Custom):${NC}"
    if command -v qrencode >/dev/null 2>&1; then
        qrencode -t ANSI256 "$final_link" 2>/dev/null || qrencode -t UTF8 "$final_link" 2>/dev/null
    fi
    ui_hr
    ui_pause
}

delete_inbound_wizard() {
    list_inbounds
    read -p " Escribe el Remark o Tag del Método a eliminar: " del_in
    [ -z "$del_in" ] && return

    inbound_line=$(grep -i "$del_in" "$V2RAY_DB" | head -n 1)
    if [ -z "$inbound_line" ]; then
        echo -e "${RED}❌ Método no encontrado.${NC}"
        ui_pause
        return
    fi

    IFS='|' read -r tid remark proto port net sec path host_header sni reality_pub <<< "$inbound_line"

    # Eliminar Inbound de config.json
    tmp_json=$(jq --arg tag "$tid" '.inbounds |= map(select(.tag != $tag))' "$V2RAY_CONF")
    echo "$tmp_json" > "$V2RAY_CONF"

    # Eliminar de la DB local
    sed -i "/^$tid|/d" "$V2RAY_DB"
    reload_v2ray_service

    echo -e "${GREEN}✅ Método Inbound '$remark' ($tid) eliminado correctamente.${NC}"
    ui_pause
}

# ==============================================================================
# MENÚ PRINCIPAL
# ==============================================================================
menu_v2ray() {
    while true; do
        clear
        ui_hr
        echo -e "${YELLOW}     GESTOR V2RAY / XRAY NATIVO (RÉPLICA EXACTA 3X-UI CLI)${NC}"
        ui_hr
        
        if check_xray_installed; then
            if systemctl is-active --quiet maximus-v2ray; then
                st="${GREEN}[ EN LÍNEA / ACTIVO ]${NC}"
            else
                st="${RED}[ DETENIDO ]${NC}"
            fi
        else
            st="${RED}[ NO INSTALADO ]${NC}"
        fi

        echo -e " Estado del Servicio: $st"
        ui_subhr
        echo -e "  ${CYAN}[1]>${WHITE} INSTALAR / REINSTALAR MOTOR XRAY-CORE${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} AGREGAR NUEVO MÉTODO / INBOUND (RÉPLICA 3X-UI)${NC}"
        echo -e "  ${CYAN}[3]>${WHITE} CREAR CLIENTE Y ASIGNAR A UN MÉTODO${NC}"
        echo -e "  ${CYAN}[4]>${WHITE} LISTAR MÉTODOS E INBOUNDS CONFIGURADOS${NC}"
        echo -e "  ${CYAN}[5]>${RED} ELIMINAR UN MÉTODO / INBOUND${NC}"
        ui_subhr
        echo -e "  ${CYAN}[6]>${WHITE} REINICIAR SERVICIO V2RAY${NC}"
        echo -e "  ${CYAN}[7]>${WHITE} VER LOGS EN TIEMPO REAL (JOURNALCTL)${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ DE PROTOCOLOS${NC}"
        ui_hr
        read -p " Selecciona una opción: " opt

        case "$opt" in
            1) install_xray_core ; ui_pause ;;
            2) add_inbound_wizard ;;
            3) create_client_wizard ;;
            4) list_inbounds ; ui_pause ;;
            5) delete_inbound_wizard ;;
            6) reload_v2ray_service ; echo -e "${GREEN}✅ Servicio V2Ray reiniciado.${NC}" ; sleep 1 ;;
            7) journalctl -u maximus-v2ray -n 50 --no-pager ; ui_pause ;;
            0) break ;;
            *) continue ;;
        esac
    done
}

menu_v2ray
