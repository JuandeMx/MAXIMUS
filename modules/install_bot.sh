#!/bin/bash
# ==========================================
# INSTALADOR INTERACTIVO MAXIMUS BOT v4.0
# ==========================================

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🛡️ Iniciando Instalación de Maximus Bot Premium...${NC}"

# 1. Instalar dependencias
echo -e "${YELLOW}[1/5] Instalando dependencias de Python...${NC}"
apt-get update -y
apt-get install -y python3-pip sqlite3
pip3 install pyTelegramBotAPI psutil

# 2. Configuración Interactiva
echo -e "${GREEN}⚙️ CONFIGURACIÓN DEL BOT${NC}"
read -p "🔹 Ingresa tu BOT_TOKEN de Telegram: " TOKEN
read -p "🔹 Ingresa tu Admin ID (puedes verlo en @userinfobot): " ADMIN_ID
read -p "🔹 Ingresa tu Dominio/Cloudflare (Opcional, Enter para omitir): " DOMAIN

# 3. Crear archivo de configuración JSON
mkdir -p /etc/MaximusVpsMx/core
cat <<EOF > /etc/MaximusVpsMx/bot_config.json
{
    "BOT_TOKEN": "$TOKEN",
    "ADMIN_ID": $ADMIN_ID,
    "HOST_DOMAIN": "$DOMAIN"
}
EOF

# 4. Eliminar Panel Web para liberar recursos (Como se solicitó)
echo -e "${RED}[3/5] Eliminando Panel Web para optimizar sistema...${NC}"
systemctl stop maximus-panel 2>/dev/null
systemctl disable maximus-panel 2>/dev/null
rm -rf /etc/MaximusVpsMx/web-panel
rm -f /etc/systemd/system/maximus-panel.service
systemctl daemon-reload

# 5. Crear Servicio del Bot
echo -e "${YELLOW}[4/5] Configurando servicio Maximus Bot...${NC}"
cat <<EOF > /etc/systemd/system/maximus-bot.service
[Unit]
Description=Maximus Elite Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/MaximusVpsMx
ExecStart=/usr/bin/python3 /etc/MaximusVpsMx/bot.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable maximus-bot
systemctl start maximus-bot

echo -e "${GREEN}✅ ¡INSTALACIÓN COMPLETADA!${NC}"
echo -e "🤖 Tu bot debe estar online en t.me/$(curl -s "https://api.telegram.org/bot$TOKEN/getMe" | jq -r '.result.username')"
