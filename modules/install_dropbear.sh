#!/bin/bash
# Instalador Dinámico Dropbear SSH

echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m             INSTALADOR DROPBEAR SSH\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
read -p " ¿En qué puerto deseas instalar Dropbear SSH? (ej: 44, 443, etc): " drop_port

if [[ -z "$drop_port" ]]; then
    echo -e "\e[1;31m❌ Cancelado. Puerto inválido.\e[0m"
    sleep 2
    exit 1
fi

echo -e "\n\e[1;32m[+] Instalando y configurando motor Dropbear en puerto $drop_port...\e[0m"

# Instalar paquete Dropbear
DEBIAN_FRONTEND=noninteractive apt-get install -y dropbear 2>/dev/null

# Generar llaves criptográficas de Dropbear (por si falta)
mkdir -p /etc/dropbear
dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key 2>/dev/null
dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key 2>/dev/null
dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key 2>/dev/null

# Limpiar config vieja y escribir la correcta
cat > /etc/default/dropbear << DROPCONF
NO_START=0
DROPBEAR_PORT=$drop_port
DROPBEAR_EXTRA_ARGS="-b /etc/issue.net"
DROPBEAR_BANNER=""
DROPBEAR_RECEIVE_WINDOW=65536
DROPCONF

# Autorizar /bin/false para usuarios túnel
grep -q "/bin/false" /etc/shells || echo "/bin/false" >> /etc/shells

# Desactivar socket mode (Ubuntu 24.04 mitigación)
systemctl stop dropbear.socket 2>/dev/null || true
systemctl disable dropbear.socket 2>/dev/null || true
systemctl mask dropbear.socket 2>/dev/null || true

# Crear override para systemd
mkdir -p /etc/systemd/system/dropbear.service.d
cat > /etc/systemd/system/dropbear.service.d/override.conf << OVERRIDE
[Service]
ExecStart=
ExecStart=/usr/sbin/dropbear -F -p $drop_port -b /etc/issue.net -r /etc/dropbear/dropbear_rsa_host_key -r /etc/dropbear/dropbear_ecdsa_host_key
OVERRIDE

# Abrir ufw
ufw allow ${drop_port}/tcp 2>/dev/null

# Aplicar persistencia
systemctl daemon-reload
systemctl enable dropbear 2>/dev/null
systemctl restart dropbear
echo -e "\e[1;32m[✓] Dropbear activo en puerto $drop_port.\e[0m"
sleep 3
