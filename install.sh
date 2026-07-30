#!/bin/bash
# MaximusVpsMx - Master Installer
# Target: Ubuntu 20.04 - 24.04 LTS

if [ "$EUID" -ne 0 ]; then
  echo -e "\e[1;31m[!] ERROR: Este instalador requiere privilegios de ROOT.\e[0m"
  echo -e "\e[1;33m[TIP] Ejecuta 'sudo su' antes de correr este comando.\e[0m"
  exit 1
fi

# Evitar bucle infinito en la actualización
if [[ "$1" == --* ]]; then
    CLIENT_KEY="${1#--}"
fi

if [ -z "$MAXIMUS_UPDATED" ]; then
    export MAXIMUS_UPDATED=1
    
    # Instalación Inicial o Actualización
    if [ ! -d "core" ] || [ ! -d "modules" ] || [ ! -f "MX" ] || [ -n "$CLIENT_KEY" ]; then
        
        # Si NO hay MASTER_IP, es directo desde GitHub
        if [ -z "$MASTER_IP" ]; then
            if [ -f "/etc/MaximusVpsMx/.master_node" ]; then
                echo -e "\e[1;36m[+] Actualización de Nodo Maestro detectada automáticamente.\e[0m"
            else
                echo -e "\e[1;36m[+] Instalación directa desde Repositorio detectada.\e[0m"
                read -p "¿Deseas instalar este VPS como el NODO MAESTRO (Vendedor)? [s/n]: " is_master
                if [[ "$is_master" == "s" || "$is_master" == "S" ]]; then
                    echo -e "\e[1;32m[+] Configurando como Nodo Maestro...\e[0m"
                    mkdir -p /etc/MaximusVpsMx
                    touch /etc/MaximusVpsMx/.master_node
                else
                    echo -e "\e[1;33m[!] Instalación de cliente. Necesitas una Key y la IP de tu proveedor.\e[0m"
                    read -p "Ingresa la IP del Servidor Maestro: " MASTER_IP
                    read -p "Ingresa tu Licencia (Key): " CLIENT_KEY
                    MASTER_PORT="6767"
                fi
            fi
        fi

        if [ ! -f "/etc/MaximusVpsMx/.master_node" ]; then
            # Preparar MASTER_URL
            if [ -z "$MASTER_URL" ]; then
                MASTER_URL="http://$MASTER_IP:$MASTER_PORT"
            fi
            
            check_key_status() {
                local key_to_check="$1"
                local response=""
                local exit_code=0
                
                if [ -n "$MASTER_URL" ]; then
                    response=$(curl -4 -sL --max-time 5 "$MASTER_URL/check?key=$key_to_check" 2>/dev/null)
                    exit_code=$?
                else
                    response=$(curl -4 -sL --max-time 5 "http://$MASTER_IP:$MASTER_PORT/check?key=$key_to_check" 2>/dev/null)
                    exit_code=$?
                fi
                
                if [ $exit_code -ne 0 ] || [ -z "$response" ]; then
                    echo "CONN_ERROR"
                    return
                fi
                
                if [[ "$response" == *"<html"* ]] || [[ "$response" == *"<HTML"* ]] || [[ "$response" == *"502 Bad Gateway"* ]] || [[ "$response" == *"504 Gateway"* ]]; then
                    echo "CONN_ERROR"
                    return
                fi
                
                if [[ "$response" == OK* ]]; then
                    echo "$response"
                elif [[ "$response" == "BANNED:IP_MISMATCH" ]]; then
                    echo "BANNED:IP_MISMATCH"
                elif [[ "$response" == "EXPIRED" ]]; then
                    echo "EXPIRED"
                elif [[ "$response" == *"Invalid Key"* ]] || [[ "$response" == *"Forbidden"* ]] || [[ "$response" == *"403"* ]] || [[ "$response" == *"Missing Key"* ]] || [[ "$response" == *"400"* ]]; then
                    echo "INVALID"
                else
                    echo "CONN_ERROR"
                fi
            }

            attempts=0
            while true; do
                # Pedir Key si no se pasó por argumento o si falló el intento previo
                if [ -z "$CLIENT_KEY" ]; then
                    echo -e ""
                    read -p "🔑 Ingresa tu Licencia (Key): " CLIENT_KEY
                fi
                
                # Limpiar espacios o caracteres invisibles que se copian por error
                CLIENT_KEY=$(echo "$CLIENT_KEY" | tr -d '\r' | tr -d ' ')
                
                echo -e "\e[1;36m[+] Verificando Licencia...\e[0m"
                LIC_STATUS=$(check_key_status "$CLIENT_KEY")
                
                if [[ "$LIC_STATUS" == OK* ]]; then
                    LIC_TYPE=$(echo "$LIC_STATUS" | cut -d':' -f2)
                    echo -e "\e[1;32m✅ Key validada exitosamente.\e[0m"
                    if [ "$LIC_TYPE" == "ILIMITED" ]; then
                        echo -e "\e[1;36m[⭐] Licencia asignada: ILIMITADA\e[0m"
                    else
                        echo -e "\e[1;36m[⏳] Licencia asignada: 30 DÍAS\e[0m"
                    fi
                    sleep 2
                    break
                elif [ "$LIC_STATUS" = "CONN_ERROR" ]; then
                    echo -e "\e[1;31m[!] ERROR: No se pudo conectar con el Maestro. Verifique su conexión.\e[0m"
                    exit 1
                else
                    attempts=$((attempts + 1))
                    echo -e "\e[1;31m[!] ERROR: Licencia expirada, bloqueada o IP inválida ($attempts/3).\e[0m"
                    echo -e "\e[1;33m[DEBUG] Conectado a: $MASTER_URL/check?key=$CLIENT_KEY\e[0m"
                    echo -e "\e[1;33m[DEBUG] El servidor respondió: $LIC_STATUS\e[0m"
                    
                    if [ "$attempts" -ge 3 ]; then
                        echo -e "\e[1;31m[!] Se ha superado el número de intentos permitidos.\e[0m"
                        if [ -d "/etc/MaximusVpsMx" ]; then
                            echo -e "\e[1;31m[!] Iniciando protocolo de seguridad Anti-Robo...\e[0m"
                            sleep 2
                            cd /root || cd /tmp
                            rm -rf /etc/MaximusVpsMx >/dev/null 2>&1
                            rm -f /usr/local/bin/MX /usr/local/bin/menu /usr/local/bin/MENU >/dev/null 2>&1
                            echo -e "\e[1;31mPanel eliminado.\e[0m"
                        fi
                        exit 1
                    fi
                    CLIENT_KEY=""
                fi
            done

            rm -rf /tmp/MaximusVpsMx 2>/dev/null
            mkdir -p /tmp/MaximusVpsMx
            echo -e "\e[1;33m[+] Descargando Archivos Premium [====================] 100%\e[0m"
            curl -4 -sL "$MASTER_URL/download?key=$CLIENT_KEY" -o /tmp/payload.run
            
            if [ ! -s /tmp/payload.run ]; then
                 echo -e "\e[1;31m[!] ERROR al descargar el instalador del servidor maestro.\e[0m"
                 exit 1
            fi
            
            chmod +x /tmp/payload.run
            cd /tmp || exit
            ./payload.run --target /tmp/MaximusVpsMx
            cd /tmp/MaximusVpsMx || exit
        else
            echo -e "\e[1;36m[+] Descargando repositorio oficial para el Maestro...\e[0m"
            pkill -9 -f '[k]ey_server.py' >/dev/null 2>&1
            pkill -9 -f '[c]loudflared' >/dev/null 2>&1
            rm -rf /tmp/MaximusVpsMx 2>/dev/null
            git clone https://github.com/JuandeMx/MAXIMUS.git /tmp/MaximusVpsMx
            cd /tmp/MaximusVpsMx || exit
            
            # Descargar Cloudflared
            if [ ! -f "/usr/local/bin/cloudflared" ]; then
                echo -e "\e[1;36m[+] Instalando Motor Anti-Firewall (Cloudflare)...\e[0m"
                ARCH=$(uname -m)
                if [[ "$ARCH" == "aarch64" ]]; then
                    curl -4 -sL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64" -o /usr/local/bin/cloudflared
                else
                    curl -4 -sL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" -o /usr/local/bin/cloudflared
                fi
                chmod +x /usr/local/bin/cloudflared
            fi
        fi
            
            chmod +x install.sh 2>/dev/null
            echo -e "\e[1;32m[+] Iniciando ejecución del instalador cliente...\e[0m"
            export MASTER_IP MASTER_PORT MASTER_URL CLIENT_KEY
            exec ./install.sh
            echo -e "\e[1;31m[!] ERROR FATAL: No se pudo iniciar el instalador cliente.\e[0m"
            exit 1
        fi
    fi

echo -e "\n\e[1;36m=========================================================\e[0m"
if [ -f "/etc/MaximusVpsMx/.master_node" ]; then
    echo -e "\e[1;33m          MAXIMUS ELITE PANEL - MASTER INSTALLER         \e[0m"
else
    echo -e "\e[1;33m          MAXIMUS ELITE PANEL - CLIENT INSTALLER         \e[0m"
fi
echo -e "\e[1;36m=========================================================\e[0m\n"

# 0. Limpieza y Preparación de Terreno (v6.2 Residual Fix)
echo -e "\e[1;32m[+] Detectando y deteniendo servicios para una instalación limpia...\e[0m"
SERVICES=("stunnel4" "ws-epro" "mx-proxy" "badvpn" "hysteria" "udp-custom" "mx-slowdns" "dropbear" "mx-webpanel" "maximus-bot" "maximus-wa" "maximus-api")
for srv in "${SERVICES[@]}"; do
    echo -e "\e[1;33m    - Deteniendo y deshabilitando $srv...\e[0m"
    systemctl stop "$srv" 2>/dev/null
    systemctl disable "$srv" 2>/dev/null
    # Eliminar definición de servicio antigua para evitar falsos positivos
    rm -f /etc/systemd/system/${srv}.service 2>/dev/null
done

# Recargar daemon inmediatamente para que systemd olvide las configuraciones antes de matar los procesos
systemctl daemon-reload 2>/dev/null

# Matar procesos por nombre (Limpieza Nuclear)
killall -9 badvpn-udpgw hysteria udp-custom stunnel4 2>/dev/null
pkill -9 badvpn-udpgw 2>/dev/null
pkill -9 hysteria 2>/dev/null
pkill -9 udp-custom 2>/dev/null
pkill -9 stunnel4 2>/dev/null
pkill -9 -f '[k]ey_server.py' >/dev/null 2>&1
pkill -9 -f '[b]ot.py' >/dev/null 2>&1
pkill -9 -f '[c]loudflared' >/dev/null 2>&1
# Liberar puertos por la fuerza bruta si quedaron zombies
fuser -k 6767/tcp >/dev/null 2>&1
fuser -k 80/tcp >/dev/null 2>&1
fuser -k 443/tcp >/dev/null 2>&1
systemctl daemon-reload


instalar_psutil_local() {
    local ARCH=$(uname -m)
    local ARCH_DEB="amd64"
    if [[ "$ARCH" == "aarch64" ]]; then
        ARCH_DEB="arm64"
    fi
    
    # Detectar SO y versión
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        local OS_NAME=$(echo "$ID" | tr '[:upper:]' '[:lower:]')
        local OS_VER=$(echo "$VERSION_ID" | cut -d. -f1)
    else
        local OS_NAME="ubuntu"
        local OS_VER="22"
    fi

    # Determinar qué deb local usar
    local DEB_NAME=""
    if [[ "$OS_NAME" == "ubuntu" ]]; then
        if [[ "$OS_VER" == "20" ]]; then
            DEB_NAME="python3-psutil_ubuntu20_${ARCH_DEB}.deb"
        elif [[ "$OS_VER" == "24" ]]; then
            DEB_NAME="python3-psutil_ubuntu24_${ARCH_DEB}.deb"
        else
            DEB_NAME="python3-psutil_ubuntu22_${ARCH_DEB}.deb"
        fi
    elif [[ "$OS_NAME" == "debian" ]]; then
        if [[ "$OS_VER" == "11" ]]; then
            DEB_NAME="python3-psutil_debian11_${ARCH_DEB}.deb"
        else
            DEB_NAME="python3-psutil_debian12_${ARCH_DEB}.deb"
        fi
    else
        DEB_NAME="python3-psutil_ubuntu22_${ARCH_DEB}.deb"
    fi

    local DEB_FILE=""
    local S_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
    if [ -f "$S_DIR/modules/offline/deb/$DEB_NAME" ]; then
        DEB_FILE="$S_DIR/modules/offline/deb/$DEB_NAME"
    elif [ -f "/etc/MaximusVpsMx/modules/offline/deb/$DEB_NAME" ]; then
        DEB_FILE="/etc/MaximusVpsMx/modules/offline/deb/$DEB_NAME"
    fi

    if ! python3 -c "import psutil" 2>/dev/null; then
        if [ -n "$DEB_FILE" ] && [ -f "$DEB_FILE" ]; then
            echo -e "\e[1;33m[⚠️] apt no pudo instalar python3-psutil. Instalando paquete local: $(basename $DEB_FILE)... \e[0m"
            dpkg -i "$DEB_FILE" >/dev/null 2>&1
            apt-get install -y -f >/dev/null 2>&1
        else
            echo -e "\e[1;33m[⚠️] Instalando psutil vía pip3 fallback...\e[0m"
            pip3 install psutil --break-system-packages >/dev/null 2>&1 || pip3 install psutil >/dev/null 2>&1
        fi
    fi
}

# 1. Update and Dependencies
echo -e "\e[1;32m[+] Actualizando repositorios e instalando dependencias...\e[0m"
# Eliminar repositorios defectuosos comunes en proveedores (Hostinger Monarx) para evitar bloqueos
rm -f /etc/apt/sources.list.d/monarx.list 2>/dev/null
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip python3-psutil squid net-tools curl wget iptables vnstat cron ufw ncurses-bin jq cmake make gcc build-essential g++ netcat-openbsd openssl psmisc screen

# Asegurar la correcta instalación de psutil
instalar_psutil_local

# Instalar pycryptodome para el generador de perfiles .MX
pip3 install pycryptodome --break-system-packages >/dev/null 2>&1 || pip3 install pycryptodome >/dev/null 2>&1

# 1.5 Firewall Local
echo -e "\e[1;32m[+] Blindando Puertos Nativos con UFW...\e[0m"
ufw allow 22/tcp 2>/dev/null
ufw allow 44/tcp 2>/dev/null
ufw allow 80/tcp 2>/dev/null
ufw allow 443/tcp 2>/dev/null
ufw allow 8080/tcp 2>/dev/null
ufw allow 7300/udp 2>/dev/null
ufw allow 54321/tcp 2>/dev/null
ufw allow 6767/tcp 2>/dev/null
# ufw allow 8082/tcp (Web Panel Desactivado)
ufw --force enable

# 2. Archivos y Rutas
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

echo -e "\e[1;32m[+] Copiando estructura de directorios a /etc/MaximusVpsMx...\e[0m"
mkdir -p /etc/MaximusVpsMx/core
mkdir -p /etc/MaximusVpsMx/modules
mkdir -p /var/log/MaximusVpsMx

# Limpieza Nuclear del Panel Web para asegurar v2.5
rm -rf /etc/MaximusVpsMx/web-panel

cp -r "$SCRIPT_DIR/"* /etc/MaximusVpsMx/
chmod +x /etc/MaximusVpsMx/MX
chmod +x /etc/MaximusVpsMx/core/*.sh 2>/dev/null
chmod +x /etc/MaximusVpsMx/core/*.py 2>/dev/null
chmod +x /etc/MaximusVpsMx/modules/*.sh 2>/dev/null
touch /etc/MaximusVpsMx/hysteria_users.db

# Inicializar entorno V2Ray
mkdir -p /etc/MaximusVpsMx/v2ray
touch /etc/MaximusVpsMx/v2ray_inbounds.db
touch /etc/MaximusVpsMx/v2ray_clients.db
if [ ! -f /etc/MaximusVpsMx/v2ray/config.json ] || [ ! -s /etc/MaximusVpsMx/v2ray/config.json ]; then
    cat << 'EOF' > /etc/MaximusVpsMx/v2ray/config.json
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

# Configurar Banner Dinámico vía PAM
sed -i 's/\r$//' /etc/MaximusVpsMx/core/maximus_banner.sh 2>/dev/null
chmod +x /etc/MaximusVpsMx/core/maximus_banner.sh

# Inicializar banner chico por defecto si no existe
if [ ! -f /etc/MaximusVpsMx/core/small_banner.txt ]; then
    echo "[LEGION ANONYMUS & MAXIMUS J&J] Si te revendieron este servidor TE ESTAFARON - Grupos: https://chat.whatsapp.com/L05wZezLROk2QIqubI0OXg | https://chat.whatsapp.com/Gmti2GoprFa0Uf4tuGD4dP?s=cl&p=a&ilr=0" > /etc/MaximusVpsMx/core/small_banner.txt
fi

# Extraer y actualizar banners estáticos para Dropbear y openSSH
if [ -f /etc/MaximusVpsMx/core/maximus_banner.sh ]; then
    html_content=$(sed -n "/cat << 'EOF'/,/^EOF/p" /etc/MaximusVpsMx/core/maximus_banner.sh | sed '1d;$d')
    mkdir -p /etc/dropbear
    echo "$html_content" > /etc/dropbear/banner
    echo "$html_content" > /etc/issue.net
fi

# Inyectar el script en el flujo de cuenta SSH (account phase para soporte OpenSSH y Dropbear)
sed -i '/maximus_banner.sh/d' /etc/pam.d/sshd
echo "account optional pam_exec.so stdout /etc/MaximusVpsMx/core/maximus_banner.sh" >> /etc/pam.d/sshd


# Migrar automáticamente a los usuarios existentes de vuelta a /bin/false
sed -i 's|/bin/maximus_shell|/bin/false|g' /etc/passwd 2>/dev/null
rm -f /bin/maximus_shell

# 3. Optimización Automática y Limpieza del Sistema (Cron)
echo -e "\e[1;32m[+] Configurando sistema de auto-limpieza (Cron & Journald)...\e[0m"
# Limitar Logs de Systemd a 50MB (Para que no sature el disco con Gigas de logs)
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/maximus-limits.conf << 'EOF'
[Journal]
SystemMaxUse=50M
MaxRetentionSec=1month
EOF
systemctl restart systemd-journald 2>/dev/null

# Aplicar Optimización de Red y Sistema (NUEVO v5.2)
if [ -f "$SCRIPT_DIR/core/speed_optimize.sh" ]; then
    chmod +x "$SCRIPT_DIR/core/speed_optimize.sh"
    bash "$SCRIPT_DIR/core/speed_optimize.sh"
fi

# Configurar Cron diario (A las 03:00 AM) para limpieza profunda
if ! grep -q "auto_clean.sh" /etc/crontab; then
    echo "0 3 * * * root /etc/MaximusVpsMx/core/auto_clean.sh" >> /etc/crontab
    systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null
fi

# Compatibilidad Legacy para OpenSSH (HTTP Custom antiguo)
echo -e "\e[1;32m[+] Configurando algoritmos legacy en OpenSSH...\e[0m"
cat > /etc/ssh/sshd_config.d/01-legacy-algorithms.conf << 'EOF'
KexAlgorithms +diffie-hellman-group1-sha1,diffie-hellman-group14-sha1
Ciphers +aes128-cbc,aes256-cbc
HostKeyAlgorithms +ssh-rsa
PubkeyAcceptedKeyTypes +ssh-rsa
EOF

# Estabilidad de Conexión (KeepAlive)
echo -e "\e[1;32m[+] Configurando KeepAlives en OpenSSH...\e[0m"
cat > /etc/ssh/sshd_config.d/02-keepalive.conf << 'EOF'
TCPKeepAlive yes
ClientAliveInterval 30
ClientAliveCountMax 1000
EOF

systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

# Corregir bug de Hostinger con useradd congelado (Reiniciar Logind/DBus)
systemctl restart systemd-logind 2>/dev/null || true

# 6. Global Banner por defecto (v7.2 Premium Custom)
echo -e "\e[1;32m[+] Aplicando Global Banner Pro...\e[0m"
# Limpiar /etc/motd para evitar duplicación del banner en terminales interactivas
echo "" > /etc/motd


# Forzar a OpenSSH a mostrar el Banner y habilitar compatibilidad de algoritmos para apps móviles
sed -i 's/#Banner.*/Banner \/etc\/issue.net/g' /etc/ssh/sshd_config
grep -q "^Banner /etc/issue.net" /etc/ssh/sshd_config || echo "Banner /etc/issue.net" >> /etc/ssh/sshd_config

# Limpiar posibles configuraciones previas de algoritmos para evitar duplicados
sed -i '/^KexAlgorithms/d' /etc/ssh/sshd_config
sed -i '/^Ciphers/d' /etc/ssh/sshd_config
sed -i '/^HostKeyAlgorithms/d' /etc/ssh/sshd_config
sed -i '/^PubkeyAcceptedKeyTypes/d' /etc/ssh/sshd_config
sed -i '/^PubkeyAcceptedAlgorithms/d' /etc/ssh/sshd_config

# Agregar algoritmos compatibles (SHA1, CBC ciphers, ssh-rsa)
echo "KexAlgorithms +diffie-hellman-group1-sha1,diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1" >> /etc/ssh/sshd_config
echo "Ciphers +aes128-cbc,aes256-cbc,3des-cbc,aes128-ctr,aes192-ctr,aes256-ctr" >> /etc/ssh/sshd_config
echo "HostKeyAlgorithms +ssh-rsa" >> /etc/ssh/sshd_config
echo "PubkeyAcceptedKeyTypes +ssh-rsa" >> /etc/ssh/sshd_config
echo "PubkeyAcceptedAlgorithms +ssh-rsa" >> /etc/ssh/sshd_config

systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

# 7. Menu Link Setup
echo -e "\e[1;32m[+] Preparando accesos globales (menu / MENU / MX)...\e[0m"
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/MX
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/menu
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/MENU
ln -sf /etc/MaximusVpsMx/MX /usr/bin/MX
ln -sf /etc/MaximusVpsMx/MX /usr/bin/menu
ln -sf /etc/MaximusVpsMx/MX /usr/bin/MENU
chmod 700 /etc/MaximusVpsMx/MX
chmod +x /etc/MaximusVpsMx/core/*.sh 2>/dev/null
chmod +x /etc/MaximusVpsMx/core/*.py 2>/dev/null
chmod +x /etc/MaximusVpsMx/modules/*.sh 2>/dev/null
# Create universal HWID user for invisible authentication
if ! id "mxhwid" &>/dev/null; then
    useradd -M -s /bin/false -e 2099-12-31 mxhwid 2>/dev/null
    echo "mxhwid:mxhwid" | chpasswd 2>/dev/null
fi

chmod +x /etc/MaximusVpsMx/core/speed_optimize.sh
chmod 600 /etc/MaximusVpsMx/cloudflare.conf 2>/dev/null
chmod 600 /etc/MaximusVpsMx/users.db 2>/dev/null

# Habilitar servicio Multi-Node Sync API Server (Puerto 6767) en TODOS los nodos
if [ -f /etc/MaximusVpsMx/core/maximus-node-api.service ]; then
    cp -f /etc/MaximusVpsMx/core/maximus-node-api.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable maximus-node-api >/dev/null 2>&1
    systemctl restart maximus-node-api >/dev/null 2>&1
fi

# Habilitar servicio Master Web Dashboard Backend (Puerto 8080) SOLO en Nodos Maestros
if [ -f /etc/MaximusVpsMx/.master_node ] && [ -f /etc/MaximusVpsMx/core/maximus-master-web.service ]; then
    cp -f /etc/MaximusVpsMx/core/maximus-master-web.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable maximus-master-web >/dev/null 2>&1
    systemctl restart maximus-master-web >/dev/null 2>&1
else
    systemctl stop maximus-master-web >/dev/null 2>&1
    systemctl disable maximus-master-web >/dev/null 2>&1
    rm -f /etc/systemd/system/maximus-master-web.service
fi
chmod 600 /etc/MaximusVpsMx/hysteria_users.db 2>/dev/null
chown -R root:root /etc/MaximusVpsMx



# Activación de la Key y Guardado
if [ -n "$CLIENT_KEY" ]; then
    echo -e "MASTER_URL='$MASTER_URL'\nMASTER_IP='$MASTER_IP'\nMASTER_PORT='$MASTER_PORT'\nCLIENT_KEY='$CLIENT_KEY'" > /etc/MaximusVpsMx/license.key
    chmod 600 /etc/MaximusVpsMx/license.key
    # Activar permanentemente a través del túnel seguro
    if [ -n "$MASTER_URL" ]; then
        curl -4 -sL "$MASTER_URL/activate?key=$CLIENT_KEY" >/dev/null 2>&1
    else
        curl -4 -sL "http://$MASTER_IP:$MASTER_PORT/activate?key=$CLIENT_KEY" >/dev/null 2>&1
    fi
fi

# Iniciar servidor Python y compilar automáticamente si es maestro
if [ -f "/etc/MaximusVpsMx/.master_node" ]; then
    echo -e "\e[1;36m[+] Creando copia de seguridad local en /var/MaximusVpsMx_backup...\e[0m"
    rm -rf /var/MaximusVpsMx_backup 2>/dev/null
    mkdir -p /var/MaximusVpsMx_backup
    cp -r "$SCRIPT_DIR"/* /var/MaximusVpsMx_backup/
    rm -f /var/MaximusVpsMx_backup/keys.db /var/MaximusVpsMx_backup/cloudflare.conf /var/MaximusVpsMx_backup/domain.conf /var/MaximusVpsMx_backup/.master_node /var/MaximusVpsMx_backup/license.key 2>/dev/null

    echo -e "\e[1;36m[+] Instalando y configurando Servidor de Keys como Servicio (Systemd)...\e[0m"
    
    # Detener servicios antiguos si existen
    systemctl stop maximus-tunnel 2>/dev/null
    systemctl stop maximus-keyserver 2>/dev/null
    
    # Matar cualquier proceso huérfano / zombie anterior para liberar el puerto
    pkill -9 -f '[k]ey_server.py' >/dev/null 2>&1
    pkill -9 -f '[c]loudflared' >/dev/null 2>&1
    fuser -k 6767/tcp >/dev/null 2>&1
    
    # Copiar definiciones de servicios
    cp /etc/MaximusVpsMx/core/maximus-keyserver.service /etc/systemd/system/ 2>/dev/null
    cp /etc/MaximusVpsMx/core/maximus-tunnel.service /etc/systemd/system/ 2>/dev/null
    systemctl daemon-reload
    
    # Asegurar permisos en script de tunnel
    chmod +x /etc/MaximusVpsMx/core/maximus_tunnel.sh 2>/dev/null
    
    # Habilitar e iniciar Keyserver
    systemctl enable maximus-keyserver 2>/dev/null
    systemctl start maximus-keyserver 2>/dev/null
    
    # Iniciar túnel si estaba habilitado
    if systemctl is-enabled --quiet maximus-tunnel 2>/dev/null; then
        systemctl start maximus-tunnel 2>/dev/null
    fi
    
    echo -e "\e[1;36m[+] Compilando paquete binario para los Clientes...\e[0m"
    if [ -f /etc/MaximusVpsMx/compilar.sh ]; then
        cd /etc/MaximusVpsMx && bash compilar.sh >/dev/null 2>&1
    fi
fi

# Configuracion de root
echo -e "\n\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m       CONFIGURACIÓN DE ACCESO ROOT (VPS CLOUD)          \e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;37m¿Deseas configurar/cambiar la contraseña de root y habilitar el login SSH por contraseña?\e[0m"
echo -e "\e[1;37m(Recomendado si usas AWS, Google Cloud, Azure u Oracle)\e[0m"
read -p "Opción [s/n]: " set_root
if [[ "$set_root" == "s" || "$set_root" == "S" ]]; then
    read -s -p "Ingresa la nueva contraseña para root: " root_pass1
    echo ""
    read -s -p "Confirma la contraseña: " root_pass2
    echo ""
    if [[ "$root_pass1" == "$root_pass2" && -n "$root_pass1" ]]; then
        echo "root:$root_pass1" | chpasswd
        if [ $? -eq 0 ]; then
            # Habilitar login por SSH forzando las opciones
            sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config
            sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config
            
            # Asegurar que existan si no estaban comentadas
            grep -q "^PermitRootLogin" /etc/ssh/sshd_config || echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
            grep -q "^PasswordAuthentication" /etc/ssh/sshd_config || echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config
            
            if [ -d /etc/ssh/sshd_config.d ]; then
                sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config.d/*.conf 2>/dev/null
                sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config.d/*.conf 2>/dev/null
                # Archivo definitivo para overriding en Cloud
                echo "PermitRootLogin yes" > /etc/ssh/sshd_config.d/99-maximus-root.conf
                echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config.d/99-maximus-root.conf
            fi
            systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null
            echo -e "\e[1;32m[+] Contraseña de root actualizada y acceso SSH habilitado.\e[0m"
        else
            echo -e "\e[1;31m[!] Error al cambiar la contraseña de root.\e[0m"
        fi
    else
        echo -e "\e[1;31m[!] Las contraseñas no coinciden o están vacías. Saltando paso...\e[0m"
    fi
fi

# Fin de Instalación
echo -e "\n\e[1;36m=========================================================\e[0m"
echo -e "\e[1;32m   [+] INSTALACIÓN DE MAXIMUS ELITE PANEL COMPLETADA.    \e[0m"
echo -e "\e[1;33m   [!] CONFIGURACIÓN BOT: MX -> Sistema -> Telegram Bot\e[0m"
echo -e "\e[1;36m=========================================================\e[0m\n"

