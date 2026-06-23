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

# Instalar paquete Dropbear del sistema para obtener configuraciones e integración de systemd
DEBIAN_FRONTEND=noninteractive apt-get install -y dropbear 2>/dev/null

# Compilar Dropbear con soporte para algoritmos antiguos (compatibilidad con HTTP Custom)
echo -e "\e[1;33m[+] Compilando Dropbear desde código fuente con algoritmos heredados (KEX, Ciphers)...\e[0m"
mkdir -p /var/log/MaximusVpsMx
echo "=== Iniciando compilación de Dropbear ===" > /var/log/MaximusVpsMx/dropbear_compile.log

DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential zlib1g-dev wget bzip2 libcrypt-dev libxcrypt-dev >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1

cd /tmp
rm -rf dropbear-2025.89*
if wget -q https://matt.ucc.asn.au/dropbear/releases/dropbear-2025.89.tar.bz2 || wget -q https://dropbear.nl/mirror/releases/dropbear-2025.89.tar.bz2; then
    tar -xf dropbear-2025.89.tar.bz2 >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1
    cd dropbear-2025.89
    
    # Escribir localoptions.h para habilitar todos los algoritmos antiguos
    cat <<EOF > localoptions.h
#define DROPBEAR_DH_GROUP1 1
#define DROPBEAR_DH_GROUP1_SHA1 1
#define DROPBEAR_DH_GROUP14_SHA1 1
#define DROPBEAR_DH_GROUP14_SHA256 1
#define DROPBEAR_ENABLE_CBC_MODE 1
#define DROPBEAR_AES128_CBC 1
#define DROPBEAR_AES256_CBC 1
#define DROPBEAR_3DES 1
#define DROPBEAR_BLOWFISH 1
#define DROPBEAR_RSA 1
#define DROPBEAR_RSA_SHA1 1
EOF

    echo "[+] Ejecutando ./configure..." >> /var/log/MaximusVpsMx/dropbear_compile.log
    ./configure >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1
    
    echo "[+] Ejecutando make..." >> /var/log/MaximusVpsMx/dropbear_compile.log
    if make -j$(nproc) >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1; then
        systemctl stop dropbear.socket 2>/dev/null || true
        systemctl stop dropbear 2>/dev/null || true
        cp -f dropbear /usr/sbin/dropbear
        cp -f dropbearkey /usr/bin/dropbearkey
        cp -f dropbearconvert /usr/bin/dropbearconvert
        echo -e "\e[1;32m[✓] Dropbear optimizado y compilado exitosamente.\e[0m"
    else
        echo -e "\e[1;31m❌ Error al compilar. Se usará el binario predeterminado del sistema.\e[0m"
        echo -e "\e[1;33m--- DETALLE DEL ERROR DE COMPILACIÓN (Últimas 20 líneas) ---\e[0m"
        tail -n 20 /var/log/MaximusVpsMx/dropbear_compile.log
    fi
else
    echo -e "\e[1;31m❌ No se pudo descargar el código fuente. Se usará el binario predeterminado del sistema.\e[0m"
fi
cd /tmp




# Generar llaves criptográficas de Dropbear (por si falta)
mkdir -p /etc/dropbear
dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key 2>/dev/null
dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key 2>/dev/null
dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key 2>/dev/null

# Limpiar config vieja y escribir la correcta
cat > /etc/default/dropbear << DROPCONF
NO_START=0
DROPBEAR_PORT=$drop_port
DROPBEAR_EXTRA_ARGS="-b /etc/issue.net -K 30 -I 0"
DROPBEAR_BANNER=""
DROPBEAR_RECEIVE_WINDOW=65536
DROPCONF

# Autorizar shells para usuarios túnel
grep -q "/bin/false" /etc/shells || echo "/bin/false" >> /etc/shells


# Desactivar socket mode (Ubuntu 24.04 mitigación)
systemctl stop dropbear.socket 2>/dev/null || true
systemctl disable dropbear.socket 2>/dev/null || true
systemctl mask dropbear.socket 2>/dev/null || true

# Eliminar posible override.conf conflictivo
rm -f /etc/systemd/system/dropbear.service.d/override.conf 2>/dev/null

# Abrir ufw
ufw allow ${drop_port}/tcp 2>/dev/null

# Aplicar persistencia
systemctl daemon-reload
systemctl enable dropbear 2>/dev/null
systemctl restart dropbear
echo -e "\e[1;32m[✓] Dropbear activo en puerto $drop_port.\e[0m"
sleep 3
