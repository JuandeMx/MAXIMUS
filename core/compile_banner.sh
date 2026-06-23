#!/bin/bash
# Extraer, limpiar y actualizar banners estáticos para Dropbear y openSSH
if [ -f /etc/MaximusVpsMx/core/maximus_banner.sh ]; then
    echo "▶ Actualizando banners estáticos (Dropbear y issue.net)..."
    html_content=$(sed -n "/cat << 'EOF'/,/^EOF/p" /etc/MaximusVpsMx/core/maximus_banner.sh | sed '1d;$d')
    mkdir -p /etc/dropbear
    echo "$html_content" > /etc/dropbear/banner
    echo "$html_content" > /etc/issue.net
    systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null
    systemctl restart dropbear 2>/dev/null
    echo "✅ Banners actualizados y servicios SSH/Dropbear reiniciados."
else
    echo "❌ No se encontró /etc/MaximusVpsMx/core/maximus_banner.sh"
fi
