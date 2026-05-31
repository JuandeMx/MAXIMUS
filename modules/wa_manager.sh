#!/bin/bash
# ==========================================
# GESTOR NATIVO DE WHATSAPP BOT - MAXIMUS MX
# ==========================================

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ui_hr() { echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"; }

# Función para instalar dependencias
install_deps() {
    echo -e "${YELLOW}[+] Verificando e instalando Node.js y dependencias del sistema...${NC}"
    
    # 1. Instalar Node.js y npm si no existen
    if ! command -v node >/dev/null 2>&1; then
        echo -e "${YELLOW}[+] Node.js no detectado. Instalando Node.js 18...${NC}"
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash - >/dev/null 2>&1
        apt-get install -y nodejs >/dev/null 2>&1
    fi
    
    if ! command -v node >/dev/null 2>&1; then
        echo -e "${RED}❌ Error: No se pudo instalar Node.js. Por favor instálelo manualmente.${NC}"
        sleep 2
        return 1
    fi
    
    echo -e "${GREEN}[OK] Node.js versión: $(node -v) detectado.${NC}"

    # 2. Instalar módulos npm locales de Baileys
    echo -e "${YELLOW}[+] Instalando módulos de Node.js locales (Baileys, Pino, QR)...${NC}"
    if [ -d "/etc/MaximusVpsMx/core/MaximusWA" ]; then
        cd /etc/MaximusVpsMx/core/MaximusWA || exit 1
        
        # Limpieza previa para evitar incompatibilidades
        rm -f package-lock.json
        rm -rf node_modules
        
        # Ejecutar instalador mostrando la salida y verificando errores
        if npm install --no-audit --no-fund; then
            echo -e "${GREEN}[OK] Módulos de Node.js instalados con éxito.${NC}"
        else
            echo -e "${YELLOW}[!] Reintentando instalación con --legacy-peer-deps...${NC}"
            if npm install --no-audit --no-fund --legacy-peer-deps; then
                echo -e "${GREEN}[OK] Módulos de Node.js instalados con éxito.${NC}"
            else
                echo -e "${RED}❌ Error: No se pudieron instalar las dependencias de Node.js.${NC}"
                echo -e "${YELLOW}Intenta ejecutar manualmente: cd /etc/MaximusVpsMx/core/MaximusWA && npm install${NC}"
                sleep 5
                return 1
            fi
        fi
    else
        echo -e "${RED}❌ Error: No se encontró el directorio /etc/MaximusVpsMx/core/MaximusWA${NC}"
        sleep 2
        return 1
    fi

    # 3. Crear el servicio de systemd para el daemon
    echo -e "${YELLOW}[+] Registrando el servicio del Bot de WhatsApp en systemd...${NC}"
    NODE_PATH=$(which node || echo "/usr/bin/node")
    cat <<EOF > /etc/systemd/system/maximus-wa.service
[Unit]
Description=Maximus WhatsApp Moderation Bot Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/etc/MaximusVpsMx/core/MaximusWA
ExecStart=$NODE_PATH bot.js
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    echo -e "${GREEN}[OK] Servicio systemd maximus-wa.service registrado exitosamente.${NC}"
    sleep 2
}

# Vincular cuenta y elegir grupos
vincular_bot() {
    clear
    ui_hr
    echo -e "       ${YELLOW}📲 VINCULAR WHATSAPP Y SELECCIONAR GRUPOS${NC}"
    ui_hr
    echo -e "1. Se detendrá el bot temporalmente (si está corriendo)."
    echo -e "2. Aparecerá un código QR grande en pantalla."
    echo -e "3. Escanéalo con tu app de WhatsApp (Dispositivos Vinculados)."
    echo -e "4. Selecciona qué grupos va a administrar el bot."
    ui_hr
    read -p "Presiona Enter para continuar..."
    
    # Detener el bot por si está activo
    systemctl stop maximus-wa 2>/dev/null
    
    cd /etc/MaximusVpsMx/core/MaximusWA || exit 1
    
    # Ejecutar en primer plano interactivo
    node get_groups.js
    
    ui_hr
    echo -e "${GREEN}Vínculo completado. Ya puedes iniciar el bot en la opción 3.${NC}"
    read -p "Presiona Enter para volver..."
}

# Principal loop
while true; do
    clear
    ui_hr
    echo -e "          ${GREEN}🤖 GESTOR DE WHATSAPP BOT PREMIUM${NC}"
    ui_hr
    
    # Detección de Estado
    systemctl is-active --quiet maximus-wa && st_wa="${GREEN}[ACTIVO]${NC}" || st_wa="${RED}[APAGADO]${NC}"
    
    echo -e "  Estado del Bot WA : $st_wa"
    ui_hr
    echo -e "  ${CYAN}[1]>${WHITE} INSTALAR / REINSTALAR MOTOR Y DEPENDENCIAS${NC}"
    echo -e "  ${CYAN}[2]>${YELLOW} VINCULAR DISPOSITIVO Y SELECCIONAR GRUPOS${NC}"
    echo -e "  ${CYAN}[3]>${GREEN} INICIAR BOT WHATSAPP${NC}"
    echo -e "  ${CYAN}[4]>${RED} DETENER BOT WHATSAPP${NC}"
    echo -e "  ${CYAN}[5]>${WHITE} VER REGISTRO DE ACTIVIDAD (LOGS)${NC}"
    ui_hr
    echo -e "  ${WHITE}[0] VOLVER AL PANEL AJUSTES${NC}"
    ui_hr
    read -p " Selecciona una opción: " opt
    
    case $opt in
        1) install_deps ;;
        2) 
            if [ ! -d "/etc/MaximusVpsMx/core/MaximusWA/node_modules" ]; then
                echo -e "${RED}❌ Error: Primero instala el motor y dependencias (Opción 1).${NC}"
                sleep 2
            else
                vincular_bot
            fi
            ;;
        3) 
            if [ ! -f "/etc/MaximusVpsMx/wa_groups.json" ]; then
                echo -e "${RED}❌ Error: Debes vincular tu dispositivo y seleccionar grupos (Opción 2).${NC}"
                sleep 2
            else
                echo -e "${YELLOW}[+] Levantando servicios de WhatsApp...${NC}"
                systemctl enable maximus-wa 2>/dev/null
                systemctl start maximus-wa 2>/dev/null
                echo -e "${GREEN}✅ Bot de WhatsApp iniciado.${NC}"
                sleep 1.5
            fi
            ;;
        4) 
            systemctl stop maximus-wa 2>/dev/null
            echo -e "${RED}⚠️ Bot de WhatsApp detenido.${NC}"
            sleep 1.5
            ;;
        5) 
            ui_hr
            journalctl -u maximus-wa -n 30 --no-pager
            ui_hr
            read -p "Presiona Enter..."
            ;;
        0) break ;;
    esac
done
