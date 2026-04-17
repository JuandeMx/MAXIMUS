#!/bin/bash
# MaximusVpsMx - Web Panel Installer v1.0 (Premium)
# Port: 8082

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

WEB_DIR="/etc/MaximusVpsMx/web-panel"

ensure_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ Solo root puede ejecutar este módulo.${NC}"
        exit 1
    fi
}

install_web_panel() {
    ensure_root
    echo -e "${CYAN}=========================================================${NC}"
    echo -e "${YELLOW}           INSTALANDO MAXIMUS WEB PANEL v1.0${NC}"
    echo -e "${CYAN}=========================================================${NC}"

    # 1. Instalar dependencias
    echo -e "${GREEN}[+] Instalando Python3-Flask...${NC}"
    apt-get update -y >/dev/null 2>&1
    apt-get install -y python3-flask python3-pip >/dev/null 2>&1
    
    # 2. Preparar Directorio
    echo -e "${GREEN}[+] Preparando archivos del proyecto...${NC}"
    mkdir -p "$WEB_DIR/backend" "$WEB_DIR/frontend"
    
    # Copiar archivos (asumiendo que están en la carpeta temporal de git)
    # CP_PATH se define durante la ejecución del panel principal
    if [ -d "./web-panel" ]; then
        cp -r ./web-panel/* "$WEB_DIR/"
    fi

    # 3. Crear Servicio Systemd
    echo -e "${GREEN}[+] Configurando servicio mx-webpanel...${NC}"
    cat > /etc/systemd/system/mx-webpanel.service <<EOF
[Unit]
Description=MaximusVpsMx Web Panel Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$WEB_DIR/backend
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    # 4. Configurar Firewall
    echo -e "${GREEN}[+] Ajustando Firewall UFW (Puerto 8082)...${NC}"
    ufw allow 8082/tcp >/dev/null 2>&1

    # 5. Iniciar
    echo -e "${GREEN}[+] Iniciando Panel Web...${NC}"
    systemctl daemon-reload
    systemctl enable mx-webpanel >/dev/null 2>&1
    systemctl restart mx-webpanel >/dev/null 2>&1

    echo -e "${CYAN}---------------------------------------------------------${NC}"
    echo -e "${GREEN}✅ Panel WEB instalado correctamente.${NC}"
    echo -e "${YELLOW} Acceso: http://$(wget -qO- ipv4.icanhazip.com):8082${NC}"
    echo -e "${CYAN}=========================================================${NC}"
}

uninstall_web_panel() {
    echo -e "${RED}[+] Eliminando Panel Web...${NC}"
    systemctl stop mx-webpanel >/dev/null 2>&1
    systemctl disable mx-webpanel >/dev/null 2>&1
    rm -f /etc/systemd/system/mx-webpanel.service
    rm -rf "$WEB_DIR"
    ufw delete allow 8082/tcp >/dev/null 2>&1
    systemctl daemon-reload
    echo -e "${GREEN}✅ Panel Web desinstalado.${NC}"
}

if [[ "$1" == "--uninstall" ]]; then
    uninstall_web_panel
else
    install_web_panel
fi
