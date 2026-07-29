#!/bin/bash
# MaximusVpsMx - Native V2Ray / Xray CLI Manager (100% Terminal)
# Modulo nativo para administrar VLESS / VMESS / TROJAN desde consola

RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
NC='\033[0m'

V2RAY_DIR="/etc/MaximusVpsMx/v2ray"
V2RAY_CONF="$V2RAY_DIR/config.json"
V2RAY_DB="/etc/MaximusVpsMx/v2ray_users.db"
XRAY_BIN="/usr/local/bin/xray"

mkdir -p "$V2RAY_DIR"
touch "$V2RAY_DB"

ui_hr() { echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"; }
ui_subhr() { echo -e "${CYAN}───────────────────────────────────────────────────────${NC}"; }
ui_pause() { read -p "Presiona Enter para continuar..." ; }

check_xray_installed() {
    if [ -x "$XRAY_BIN" ]; then
        return 0
    else
        return 1
    fi
}

install_xray_core() {
    echo -e "${CYAN}[+] Instalando dependencias (jq, qrencode, unzip, curl)...${NC}"
    apt-get update -y >/dev/null 2>&1
    apt-get install -y jq qrencode unzip curl >/dev/null 2>&1

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
    if [ ! -f "$V2RAY_CONF" ]; then
        cat << 'EOF' > "$V2RAY_CONF"
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "port": 8880,
      "protocol": "vmess",
      "settings": {
        "clients": []
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "/vmess"
        }
      },
      "tag": "vmess-in"
    },
    {
      "port": 2082,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "/vless"
        }
      },
      "tag": "vless-in"
    },
    {
      "port": 2083,
      "protocol": "trojan",
      "settings": {
        "clients": []
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "/trojan"
        }
      },
      "tag": "trojan-in"
    }
  ],
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

create_v2ray_user() {
    if ! check_xray_installed; then
        echo -e "${RED}❌ Xray-core no está instalado. Ejecuta la Opción 1 primero.${NC}"
        ui_pause
        return
    fi

    echo -e "\n${YELLOW}▶ CREAR NUEVO USUARIO V2RAY (VLESS / VMESS / TROJAN)${NC}"
    read -p " Nombre del Usuario: " user
    [ -z "$user" ] && return
    grep -qw "^$user:" "$V2RAY_DB" && { echo -e "${RED}❌ El usuario ya existe en V2Ray.${NC}"; ui_pause; return; }

    echo -e " Selecciona el protocolo:"
    echo -e "  ${CYAN}[1]${NC} VMESS (WebSocket - Puerto 8880 - Path /vmess)"
    echo -e "  ${CYAN}[2]${NC} VLESS (WebSocket - Puerto 2082 - Path /vless)"
    echo -e "  ${CYAN}[3]${NC} TROJAN (WebSocket - Puerto 2083 - Path /trojan)"
    read -p " Opción [1-3]: " proto_opt

    case "$proto_opt" in
        1) proto="vmess" ; port=8880 ; path="/vmess" ;;
        2) proto="vless" ; port=2082 ; path="/vless" ;;
        3) proto="trojan" ; port=2083 ; path="/trojan" ;;
        *) proto="vmess" ; port=8880 ; path="/vmess" ;;
    esac

    read -p " Días de validez: " dias
    [ -z "$dias" ] && dias=30
    exp_date=$(date -d "+$dias days" +%Y-%m-%d)

    uuid=$(cat /proc/sys/kernel/random/uuid)
    
    # Agregar cliente al JSON de Xray
    if [ "$proto" == "vmess" ]; then
        tmp_json=$(jq --arg id "$uuid" --arg email "$user" '.inbounds[0].settings.clients += [{"id": $id, "alterId": 0, "email": $email}]' "$V2RAY_CONF")
        echo "$tmp_json" > "$V2RAY_CONF"
    elif [ "$proto" == "vless" ]; then
        tmp_json=$(jq --arg id "$uuid" --arg email "$user" '.inbounds[1].settings.clients += [{"id": $id, "email": $email}]' "$V2RAY_CONF")
        echo "$tmp_json" > "$V2RAY_CONF"
    elif [ "$proto" == "trojan" ]; then
        tmp_json=$(jq --arg pass "$uuid" --arg email "$user" '.inbounds[2].settings.clients += [{"password": $pass, "email": $email}]' "$V2RAY_CONF")
        echo "$tmp_json" > "$V2RAY_CONF"
    fi

    echo "$user:$uuid:$proto:$exp_date:$port:$path" >> "$V2RAY_DB"
    reload_v2ray_service

    # Generar URI Link
    ip=$(curl -s4 ifconfig.me || echo "127.0.0.1")
    domain=""
    [ -f /etc/MaximusVpsMx/domain.conf ] && domain=$(cat /etc/MaximusVpsMx/domain.conf)
    [ -z "$domain" ] && domain="$ip"

    if [ "$proto" == "vmess" ]; then
        v_json=$(cat <<EOF
{
  "v": "2",
  "ps": "$user-VMESS",
  "add": "$domain",
  "port": "$port",
  "id": "$uuid",
  "aid": "0",
  "scy": "auto",
  "net": "ws",
  "type": "none",
  "host": "$domain",
  "path": "$path",
  "tls": ""
}
EOF
)
        b64_uri=$(echo -n "$v_json" | base64 -w 0)
        final_link="vmess://$b64_uri"
    elif [ "$proto" == "vless" ]; then
        final_link="vless://$uuid@$domain:$port?type=ws&security=none&path=$path#$user-VLESS"
    elif [ "$proto" == "trojan" ]; then
        final_link="trojan://$uuid@$domain:$port?type=ws&security=none&path=$path#$user-TROJAN"
    fi

    clear
    ui_hr
    echo -e "${GREEN}      ✅ USUARIO V2RAY ($proto) CREADO CON ÉXITO${NC}"
    ui_hr
    echo -e "${CYAN} USUARIO  :${WHITE} $user${NC}"
    echo -e "${CYAN} UUID / KEY:${WHITE} $uuid${NC}"
    echo -e "${CYAN} PROTOCOLO:${WHITE} $proto (WebSocket - Puerto $port - Path $path)${NC}"
    echo -e "${CYAN} EXPIRA   :${WHITE} $exp_date ($dias Días)${NC}"
    ui_subhr
    echo -e "${YELLOW} ENLACE DE CONEXIÓN (LINK):${NC}"
    echo -e "${WHITE}$final_link${NC}"
    ui_subhr
    echo -e "${YELLOW} CÓDIGO QR PARA ESCANEAR EN APP (v2rayNG / HTTP Custom):${NC}"
    if command -v qrencode >/dev/null 2>&1; then
        qrencode -t ANSI256 "$final_link" 2>/dev/null || qrencode -t UTF8 "$final_link" 2>/dev/null
    else
        echo -e "${RED}(Instala qrencode para ver el código QR impreso)${NC}"
    fi
    ui_hr
    ui_pause
}

list_v2ray_users() {
    ui_hr
    echo -e "${YELLOW}          LISTA DE USUARIOS V2RAY (XRAY CLI)${NC}"
    ui_hr
    if [ ! -s "$V2RAY_DB" ]; then
        echo -e " ${RED}No hay usuarios de V2Ray registrados.${NC}"
    else
        printf "${WHITE}%-15s | %-8s | %-36s | %-10s${NC}\n" "USUARIO" "PROTO" "UUID / KEY" "EXPIRA"
        ui_subhr
        while IFS=: read -r u id pr ex po pa; do
            [ -z "$u" ] && continue
            printf " ${CYAN}%-14s${NC} | %-8s | %-36s | %-10s\n" "$u" "$pr" "$id" "$ex"
        done < "$V2RAY_DB"
    fi
    ui_hr
    ui_pause
}

delete_v2ray_user() {
    echo -e "\n${YELLOW}▶ ELIMINAR USUARIO V2RAY${NC}"
    read -p " Escribe el Username: " user
    [ -z "$user" ] && return

    if ! grep -qw "^$user:" "$V2RAY_DB"; then
        echo -e "${RED}❌ Usuario no encontrado en V2Ray.${NC}"
        ui_pause
        return
    fi

    uuid=$(grep "^$user:" "$V2RAY_DB" | cut -d: -f2)
    proto=$(grep "^$user:" "$V2RAY_DB" | cut -d: -f3)

    # Eliminar de la DB
    sed -i "/^$user:/d" "$V2RAY_DB"

    # Eliminar del JSON de Xray
    if [ "$proto" == "vmess" ]; then
        tmp_json=$(jq --arg email "$user" '.inbounds[0].settings.clients |= map(select(.email != $email))' "$V2RAY_CONF")
        echo "$tmp_json" > "$V2RAY_CONF"
    elif [ "$proto" == "vless" ]; then
        tmp_json=$(jq --arg email "$user" '.inbounds[1].settings.clients |= map(select(.email != $email))' "$V2RAY_CONF")
        echo "$tmp_json" > "$V2RAY_CONF"
    elif [ "$proto" == "trojan" ]; then
        tmp_json=$(jq --arg email "$user" '.inbounds[2].settings.clients |= map(select(.email != $email))' "$V2RAY_CONF")
        echo "$tmp_json" > "$V2RAY_CONF"
    fi

    reload_v2ray_service
    echo -e "${GREEN}✅ Usuario $user eliminado exitosamente de V2Ray.${NC}"
    ui_pause
}

menu_v2ray() {
    while true; do
        clear
        ui_hr
        echo -e "${YELLOW}       GESTOR V2RAY / XRAY NATIVO (100% TERMINAL)${NC}"
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
        echo -e "  ${CYAN}[1]>${WHITE} INSTALAR / REINSTALAR XRAY-CORE (MOTOR OFICIAL)${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} CREAR USUARIO V2RAY (VLESS / VMESS / TROJAN)${NC}"
        echo -e "  ${CYAN}[3]>${WHITE} LISTAR USUARIOS Y UUIDS REGISTRADOS${NC}"
        echo -e "  ${CYAN}[4]>${RED} ELIMINAR UN USUARIO V2RAY${NC}"
        ui_subhr
        echo -e "  ${CYAN}[5]>${WHITE} REINICIAR / INICIAR SERVICIO V2RAY${NC}"
        echo -e "  ${CYAN}[6]>${WHITE} DETENER SERVICIO V2RAY${NC}"
        echo -e "  ${CYAN}[7]>${WHITE} VER LOGS DE CONEXIÓN EN TIEMPO REAL (JOURNALCTL)${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
        ui_hr
        read -p " Selecciona una opción: " opt

        case "$opt" in
            1) install_xray_core ; ui_pause ;;
            2) create_v2ray_user ;;
            3) list_v2ray_users ;;
            4) delete_v2ray_user ;;
            5) systemctl restart maximus-v2ray ; echo -e "${GREEN}✅ Servicio V2Ray reiniciado.${NC}" ; sleep 1 ;;
            6) systemctl stop maximus-v2ray ; echo -e "${RED}⚠️ Servicio V2Ray detenido.${NC}" ; sleep 1 ;;
            7) journalctl -u maximus-v2ray -n 50 --no-pager ; ui_pause ;;
            0) break ;;
            *) continue ;;
        esac
    done
}

menu_v2ray
