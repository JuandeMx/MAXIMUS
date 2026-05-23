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

        if [ ! -f "/etc/MaximusVpsMx/.master_node" ]; then
            
            # Pedir Key si no se pasó por argumento
            if [ -z "$CLIENT_KEY" ]; then
                echo -e ""
                read -p "🔑 Ingresa tu Licencia (Key): " CLIENT_KEY
            fi
            
            echo -e "\e[1;36m[+] Verificando Licencia...\e[0m"
            LIC_STATUS=$(curl -sL "http://$MASTER_IP:$MASTER_PORT/check?key=$CLIENT_KEY" 2>/dev/null)
            
            if [[ "$LIC_STATUS" == OK* ]]; then
                LIC_TYPE=$(echo "$LIC_STATUS" | cut -d':' -f2)
                echo -e "\e[1;32m✅ Key validada exitosamente.\e[0m"
                if [ "$LIC_TYPE" == "ILIMITED" ]; then
                    echo -e "\e[1;36m[⭐] Licencia asignada: ILIMITADA\e[0m"
                else
                    echo -e "\e[1;36m[⏳] Licencia asignada: 30 DÍAS\e[0m"
                fi
                sleep 2
            else
                 echo -e "\e[1;31m[!] ERROR: Licencia expirada, bloqueada o IP inválida.\e[0m"
                 exit 1
            fi

            rm -rf /tmp/MaximusVpsMx 2>/dev/null
            mkdir -p /tmp/MaximusVpsMx
            echo -e "\e[1;33m[+] Descargando Archivos Premium [====================] 100%\e[0m"
            curl -sL "http://$MASTER_IP:$MASTER_PORT/download?key=$CLIENT_KEY" -o /tmp/panel.tar.gz
            
            if ! tar -tzf /tmp/panel.tar.gz >/dev/null 2>&1; then
                 echo -e "\e[1;31m[!] ERROR al extraer archivos del servidor maestro.\e[0m"
                 exit 1
            fi
            
            tar -xzf /tmp/panel.tar.gz -C /tmp/MaximusVpsMx
            cd /tmp/MaximusVpsMx || exit
        else
            echo -e "\e[1;36m[+] Descargando repositorio oficial para el Maestro...\e[0m"
            rm -rf /tmp/MaximusVpsMx 2>/dev/null
            git clone https://github.com/JuandeMx/MAXIMUS.git /tmp/MaximusVpsMx
            cd /tmp/MaximusVpsMx || exit
        fi
            
            chmod +x install.sh
            echo -e "\e[1;32m[+] Iniciando ejecución del instalador cliente...\e[0m"
            exec ./install.sh
            exit 0
        fi
    fi
fi

echo -e "\n\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m          MAXIMUS ELITE PANEL - MASTER INSTALLER         \e[0m"
echo -e "\e[1;36m=========================================================\e[0m\n"

# 0. Limpieza y Preparación de Terreno (v6.2 Residual Fix)
echo -e "\e[1;32m[+] Detectando y deteniendo servicios para una instalación limpia...\e[0m"
SERVICES=("stunnel4" "ws-epro" "mx-proxy" "badvpn" "hysteria" "udp-custom" "mx-slowdns" "dropbear" "mx-webpanel" "maximus-bot")
for srv in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$srv" || systemctl is-enabled --quiet "$srv" 2>/dev/null; then
        echo -e "\e[1;33m    - Deteniendo $srv...\e[0m"
        systemctl stop "$srv" 2>/dev/null
        systemctl disable "$srv" 2>/dev/null
    fi
    # Eliminar definición de servicio antigua para evitar falsos positivos
    rm -f /etc/systemd/system/${srv}.service 2>/dev/null
done

# Matar procesos por nombre (Limpieza Nuclear)
killall -9 badvpn-udpgw hysteria udp-custom python3 stunnel4 2>/dev/null
systemctl daemon-reload


# 1. Update and Dependencies
echo -e "\e[1;32m[+] Actualizando repositorios e instalando dependencias...\e[0m"
# Eliminar repositorios defectuosos comunes en proveedores (Hostinger Monarx) para evitar bloqueos
rm -f /etc/apt/sources.list.d/monarx.list 2>/dev/null
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip squid net-tools curl wget iptables vnstat cron ufw ncurses-bin jq cmake make gcc build-essential g++ netcat-openbsd openssl

# 1.5 Firewall Local
echo -e "\e[1;32m[+] Blindando Puertos Nativos con UFW...\e[0m"
ufw allow 22/tcp 2>/dev/null
ufw allow 44/tcp 2>/dev/null
ufw allow 80/tcp 2>/dev/null
ufw allow 443/tcp 2>/dev/null
ufw allow 8080/tcp 2>/dev/null
ufw allow 7300/udp 2>/dev/null
ufw allow 54321/tcp 2>/dev/null
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
touch /etc/MaximusVpsMx/hysteria_users.db

# Configurar Banner Dinámico vía PAM
sed -i 's/\r$//' /etc/MaximusVpsMx/core/maximus_banner.sh 2>/dev/null
chmod +x /etc/MaximusVpsMx/core/maximus_banner.sh

# Inyectar el script en el flujo de autenticación SSH (auth phase)
sed -i '/maximus_banner.sh/d' /etc/pam.d/sshd
echo "auth optional pam_exec.so stdout /etc/MaximusVpsMx/core/maximus_banner.sh" >> /etc/pam.d/sshd

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
cat > /etc/issue.net << 'BANNER'
 [1;36m
   *                )  (       *            (     
 (  `     (      ( /(  )\ )  (  `           )\ )  
 )\))(    )\     )\())(()/(  )\))(      (  (()/(  
((_)()\((((_)(  ((_)\  /(_))((_)()\     )\  /(_)) 
(_()((_))\ _ )\ __((_)(_))  (_()((_) _ ((_)(_))   
|  \/  |(_)_\(_)\ \/ /|_ _| |  \/  || | | |/ __|  
| |\/| | / _ \   >  <  | |  | |\/| || |_| |\__ \  
|_|  |_|/_/ \_\ /_/\_\|___| |_|  |_| \___/ |___/  
 [0m
 [1;32m   USE LOS COMANDOS: menu , MENU o MX  [0m
 [1;33m   PARA ENTRAR AL PANEL DE ADMINISTRACION  [0m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNER
cp /etc/issue.net /etc/motd

# Forzar a OpenSSH a mostrar el Banner
sed -i 's/#Banner.*/Banner \/etc\/issue.net/g' /etc/ssh/sshd_config
grep -q "^Banner /etc/issue.net" /etc/ssh/sshd_config || echo "Banner /etc/issue.net" >> /etc/ssh/sshd_config
systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

# 7. Menu Link Setup
echo -e "\e[1;32m[+] Preparando accesos globales (menu / MENU / MX)...\e[0m"
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/MX
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/menu
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/MENU
chmod 700 /etc/MaximusVpsMx/MX
chmod +x /etc/MaximusVpsMx/core/*.sh 2>/dev/null
chmod +x /etc/MaximusVpsMx/core/*.py 2>/dev/null
# Create universal HWID user for invisible authentication
if ! id "mxhwid" &>/dev/null; then
    useradd -M -s /bin/false -e 2099-12-31 mxhwid 2>/dev/null
    echo "mxhwid:mxhwid" | chpasswd 2>/dev/null
fi

chmod +x /etc/MaximusVpsMx/core/speed_optimize.sh
chmod 600 /etc/MaximusVpsMx/cloudflare.conf 2>/dev/null
chmod 600 /etc/MaximusVpsMx/users.db 2>/dev/null
chmod 600 /etc/MaximusVpsMx/hysteria_users.db 2>/dev/null
chown -R root:root /etc/MaximusVpsMx



# Activación de la Key y Guardado
if [ -n "$CLIENT_KEY" ]; then
    echo -e "MASTER_IP='$MASTER_IP'\nMASTER_PORT='$MASTER_PORT'\nCLIENT_KEY='$CLIENT_KEY'" > /etc/MaximusVpsMx/license.key
    chmod 600 /etc/MaximusVpsMx/license.key
    # Activar permanentemente
    curl -sL "http://$MASTER_IP:$MASTER_PORT/activate?key=$CLIENT_KEY" >/dev/null 2>&1
fi

# Fin de Instalación
echo -e "\n\e[1;36m=========================================================\e[0m"
echo -e "\e[1;32m   [+] INSTALACIÓN DE MAXIMUS ELITE PANEL COMPLETADA.    \e[0m"
echo -e "\e[1;33m   [!] CONFIGURACIÓN BOT: MX -> Sistema -> Telegram Bot\e[0m"
echo -e "\e[1;36m=========================================================\e[0m\n"

