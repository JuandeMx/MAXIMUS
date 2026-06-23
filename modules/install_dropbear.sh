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

echo -e "\e[1;33m[+] Instalando dependencias de compilación...\e[0m"
if ! DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential zlib1g-dev wget bzip2 libcrypt-dev >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1; then
    echo -e "\e[1;31m❌ Error al instalar dependencias de compilación.\e[0m"
    echo -e "\e[1;33m--- DETALLE DEL ERROR DE DEPENDENCIAS ---\e[0m"
    tail -n 15 /var/log/MaximusVpsMx/dropbear_compile.log
    exit 1
fi

cd /tmp
rm -rf dropbear-2022.83*
echo -e "\e[1;33m[+] Descargando código fuente de Dropbear 2022.83...\\e[0m"
if wget -q https://matt.ucc.asn.au/dropbear/releases/dropbear-2022.83.tar.bz2 || wget -q https://dropbear.nl/mirror/releases/dropbear-2022.83.tar.bz2; then
    tar -xf dropbear-2022.83.tar.bz2 >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1
    cd dropbear-2022.83
    
    # Escribir localoptions.h - SOLO macros válidas del default_options.h oficial con #undef para evitar advertencias/errores
    cat <<'LOCALOPT' > localoptions.h
#ifndef DROPBEAR_LOCALOPTIONS_H
#define DROPBEAR_LOCALOPTIONS_H

/* Habilitar CBC mode (deshabilitado por defecto) */
#undef DROPBEAR_ENABLE_CBC_MODE
#define DROPBEAR_ENABLE_CBC_MODE 1

/* Habilitar 3DES (deshabilitado por defecto) */
#undef DROPBEAR_3DES
#define DROPBEAR_3DES 1

/* Habilitar SHA1 HMAC (deshabilitado por defecto en nuevas versiones) */
#undef DROPBEAR_SHA1_HMAC
#define DROPBEAR_SHA1_HMAC 1

#undef DROPBEAR_SHA1_96_HMAC
#define DROPBEAR_SHA1_96_HMAC 1

/* Habilitar RSA con SHA1 (requerido para clientes antiguos como HTTP Custom) */
#undef DROPBEAR_RSA_SHA1
#define DROPBEAR_RSA_SHA1 1

/* Habilitar DH Group14 SHA1 y SHA256 (compatibilidad) */
#undef DROPBEAR_DH_GROUP14_SHA1
#define DROPBEAR_DH_GROUP14_SHA1 1

#undef DROPBEAR_DH_GROUP14_SHA256
#define DROPBEAR_DH_GROUP14_SHA256 1

/* Habilitar DSS (algunos clientes antiguos lo requieren) */
#undef DROPBEAR_DSS
#define DROPBEAR_DSS 1

/* Aumentar límites de Banner para soportar HTML banners grandes */
#undef MAX_BANNER_SIZE
#define MAX_BANNER_SIZE 16384

#undef MAX_BANNER_LINES
#define MAX_BANNER_LINES 100

#endif /* DROPBEAR_LOCALOPTIONS_H */
LOCALOPT

    echo -e "\e[1;33m[+] Configurando entorno (./configure)...\\e[0m"
    echo "[+] Ejecutando ./configure..." >> /var/log/MaximusVpsMx/dropbear_compile.log
    if ! ./configure >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1; then
        echo -e "\e[1;31m❌ Error en la configuración de Dropbear (./configure).\\e[0m"
        echo -e "\e[1;33m--- DETALLE DEL ERROR DE CONFIGURACIÓN ---\\e[0m"
        tail -n 25 /var/log/MaximusVpsMx/dropbear_compile.log
        cd /tmp
        exit 1
    fi
    
    echo -e "\e[1;33m[+] Compilando binarios (make PROGRAMS='dropbear dropbearkey')...\\e[0m"
    echo "[+] Ejecutando make..." >> /var/log/MaximusVpsMx/dropbear_compile.log
    if make clean >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1 && make PROGRAMS="dropbear dropbearkey" -j$(nproc) >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1; then
        systemctl stop dropbear.socket 2>/dev/null || true
        systemctl stop dropbear 2>/dev/null || true
        cp -f dropbear /usr/sbin/dropbear
        cp -f dropbearkey /usr/bin/dropbearkey
        [ -f dropbearconvert ] && cp -f dropbearconvert /usr/bin/dropbearconvert
        echo -e "\e[1;32m[✓] Dropbear optimizado y compilado exitosamente.\\e[0m"
    else
        echo -e "\e[1;31m❌ Error al compilar (make). Se usará el binario predeterminado del sistema.\\e[0m"
        echo -e "\e[1;33m--- DETALLE DEL ERROR DE COMPILACIÓN (Últimas 30 líneas) ---\\e[0m"
        tail -n 30 /var/log/MaximusVpsMx/dropbear_compile.log
        cd /tmp
        exit 1
    fi
else
    echo -e "\e[1;31m❌ No se pudo descargar el código fuente. Se usará el binario predeterminado del sistema.\\e[0m"
    exit 1
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
DROPBEAR_EXTRA_ARGS="-b /etc/dropbear/banner -K 30 -I 0"
DROPBEAR_BANNER="/etc/dropbear/banner"
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
