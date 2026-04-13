#!/bin/bash
# MaximusVpsMx - Master Installer
# Target: Ubuntu 20.04 - 24.04 LTS

if [ "$EUID" -ne 0 ]; then
  echo "Por favor, corre este script como root (sudo su)"
  exit 1
fi

echo -e "\n\e[1;36m=========================================================\e[0m"
echo -e "\e[1;36m          Iniciando Instalación de MaximusVpsMx          \e[0m"
echo -e "\e[1;36m=========================================================\e[0m\n"

# 1. Update and Dependencies
echo -e "\e[1;32m[+] Actualizando repositorios e instalando dependencias...\e[0m"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip dropbear stunnel4 squid net-tools curl wget iptables vnstat cron ufw ncurses-bin jq cmake make gcc build-essential g++ netcat-openbsd

# 1.5 Firewall Local
echo -e "\e[1;32m[+] Blindando Puertos Nativos con UFW...\e[0m"
ufw allow 22/tcp 2>/dev/null
ufw allow 44/tcp 2>/dev/null
ufw allow 80/tcp 2>/dev/null
ufw allow 443/tcp 2>/dev/null
ufw allow 7300/udp 2>/dev/null
ufw --force enable

# 2. Archivos y Rutas
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

echo -e "\e[1;32m[+] Copiando estructura de directorios a /etc/MaximusVpsMx...\e[0m"
mkdir -p /etc/MaximusVpsMx/core
mkdir -p /etc/MaximusVpsMx/modules
mkdir -p /var/log/MaximusVpsMx

cp -r "$SCRIPT_DIR/"* /etc/MaximusVpsMx/
chmod +x /etc/MaximusVpsMx/MX
chmod +x /etc/MaximusVpsMx/core/PDirect.py



# Compatibilidad Legacy para OpenSSH (HTTP Custom antiguo)
echo -e "\e[1;32m[+] Configurando algoritmos legacy en OpenSSH...\e[0m"
cat > /etc/ssh/sshd_config.d/01-legacy-algorithms.conf << 'EOF'
KexAlgorithms +diffie-hellman-group1-sha1,diffie-hellman-group14-sha1
Ciphers +aes128-cbc,aes256-cbc
HostKeyAlgorithms +ssh-rsa
PubkeyAcceptedKeyTypes +ssh-rsa
EOF
systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

# Corregir bug de Hostinger con useradd congelado (Reiniciar Logind/DBus)
systemctl restart systemd-logind 2>/dev/null || true

# 6. Global Banner por defecto
echo -e "\e[1;32m[+] Aplicando Global Banner...\e[0m"
cat > /etc/issue.net << 'BANNER'
                       (  )
                      (    )
                     (  /\  )
                      \/  \/
                      / /\ \
                     /_/  \_\

        +--------------------------------------------+
        |                 FREE LATAM                 |
        |            Secure SSH Access Node          |
        |        Authorized connections only         |
        +--------------------------------------------+
BANNER

# Forzar a OpenSSH a mostrar el Banner
sed -i 's/#Banner.*/Banner \/etc\/issue.net/g' /etc/ssh/sshd_config
grep -q "^Banner /etc/issue.net" /etc/ssh/sshd_config || echo "Banner /etc/issue.net" >> /etc/ssh/sshd_config
systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

# 7. Menu Link Setup
echo -e "\e[1;32m[+] Preparando alias global 'MX'...\e[0m"
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/MX
chmod 700 /etc/MaximusVpsMx/MX
chmod 700 /etc/MaximusVpsMx/core/PDirect.py
chmod 700 /etc/MaximusVpsMx/modules/cloudflare-ddns.sh 2>/dev/null
chmod +x /etc/MaximusVpsMx/modules/install_*.sh 2>/dev/null
chmod 600 /etc/MaximusVpsMx/cloudflare.conf 2>/dev/null
chmod 600 /etc/MaximusVpsMx/users.db 2>/dev/null
chown -R root:root /etc/MaximusVpsMx



echo -e "\n\e[1;36m=========================================================\e[0m"
echo -e "\e[1;32m[+] Instalación Base Completada.\e[0m"
echo -e "\e[1;36m=========================================================\e[0m\n"

