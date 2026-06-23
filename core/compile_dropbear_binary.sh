#!/bin/bash
# Script de compilación no interactivo para Dropbear con límite de banner de 16KB
echo "=== Compilando Dropbear con límites de banner aumentados ==="
DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1
DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential zlib1g-dev wget bzip2 libcrypt-dev >/dev/null 2>&1

cd /tmp
rm -rf dropbear-2022.83*
wget -q https://matt.ucc.asn.au/dropbear/releases/dropbear-2022.83.tar.bz2 || wget -q https://dropbear.nl/mirror/releases/dropbear-2022.83.tar.bz2
tar -xf dropbear-2022.83.tar.bz2
cd dropbear-2022.83

cat <<'LOCALOPT' > localoptions.h
#ifndef DROPBEAR_LOCALOPTIONS_H
#define DROPBEAR_LOCALOPTIONS_H

#undef DROPBEAR_ENABLE_CBC_MODE
#define DROPBEAR_ENABLE_CBC_MODE 1

#undef DROPBEAR_3DES
#define DROPBEAR_3DES 1

#undef DROPBEAR_SHA1_HMAC
#define DROPBEAR_SHA1_HMAC 1

#undef DROPBEAR_SHA1_96_HMAC
#define DROPBEAR_SHA1_96_HMAC 1

#undef DROPBEAR_RSA_SHA1
#define DROPBEAR_RSA_SHA1 1

#undef DROPBEAR_DH_GROUP14_SHA1
#define DROPBEAR_DH_GROUP14_SHA1 1

#undef DROPBEAR_DH_GROUP14_SHA256
#define DROPBEAR_DH_GROUP14_SHA256 1

#undef DROPBEAR_DSS
#define DROPBEAR_DSS 1

/* Aumentar límites de Banner para soportar HTML banners grandes */
#undef MAX_BANNER_SIZE
#define MAX_BANNER_SIZE 16384

#undef MAX_BANNER_LINES
#define MAX_BANNER_LINES 100

#endif
LOCALOPT

# Modificar sysoptions.h directamente ya que no tiene guardas #ifndef
sed -i 's/#define MAX_BANNER_SIZE 2050/#define MAX_BANNER_SIZE 16384/g' sysoptions.h
sed -i 's/#define MAX_BANNER_LINES 20/#define MAX_BANNER_LINES 100/g' sysoptions.h

echo "▶ Ejecutando ./configure..."
./configure >/dev/null 2>&1
echo "▶ Ejecutando make..."
make clean >/dev/null 2>&1
if make PROGRAMS="dropbear dropbearkey" -j$(nproc) >/dev/null 2>&1; then
    systemctl stop dropbear.socket 2>/dev/null || true
    systemctl stop dropbear 2>/dev/null || true
    cp -f dropbear /usr/sbin/dropbear
    cp -f dropbearkey /usr/bin/dropbearkey
    systemctl restart dropbear
    echo "✅ DROPBEAR RECOMPILADO CON ÉXITO Y REINICIADO."
else
    echo "❌ ERROR AL COMPILAR DROPBEAR."
fi
