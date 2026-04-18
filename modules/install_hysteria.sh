#!/bin/bash
# MaximusVpsMx - Instalador Hysteria 2
# Protocolo QUIC/UDP de alta velocidad con mascarada anti-DPI

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
WHITE='\033[1;37m'
NC='\033[0m'

echo -e "${CYAN}=========================================================${NC}"
echo -e "${YELLOW}          INSTALADOR HYSTERIA v2 (QUIC/UDP)${NC}"
echo -e "${CYAN}=========================================================${NC}"

# Puerto configurable y Rango de Port-Hopping (Instalación automática)
hy_range="2000:5000"
hy_port=36713

# Contraseña de autenticación por defecto (Automática)
hy_pass="maximus"

echo -e "\n${GREEN}[+] Preparando entorno e instalando dependencias...${NC}"
apt-get update -y && apt-get install -y python3 wget openssl 2>/dev/null

# Detectar arquitectura
ARCH=$(uname -m)
case $ARCH in
    x86_64)  BIN_ARCH="amd64"  ;;
    aarch64) BIN_ARCH="arm64"  ;;
    armv7l)  BIN_ARCH="armv7"  ;;
    *)       echo -e "${RED}❌ Arquitectura $ARCH no soportada.${NC}"; exit 1 ;;
esac

# Directorio de trabajo
HY_DIR="/etc/hysteria"
mkdir -p "$HY_DIR"

# Descargar el binario directamente desde la Bóveda de MAXIMUS (Binario blindado estable)
echo -e "${YELLOW}[+] Descargando Hysteria v2 desde la Bóveda Local Maximus...${NC}"
LATEST_URL="https://raw.githubusercontent.com/JuandeMx/MAXIMUS/main/bin/hysteria-linux-${BIN_ARCH}"

if curl -sL -f --connect-timeout 10 --max-time 60 -o "$HY_DIR/hysteria" "$LATEST_URL"; then
    echo -e "${GREEN}[✔] Descarga segura exitosa (Bóveda MAXIMUS).${NC}"
else
    echo -e "${RED}❌ Error: No se pudo conectar a la Bóveda MAXIMUS para Hysteria.${NC}"
    exit 1
fi

chmod +x "$HY_DIR/hysteria"

# Instalar motor de autenticación
echo -e "${GREEN}[+] Instalando motor de autenticación dinámico...${NC}"
mkdir -p /etc/MaximusVpsMx/core
cat > /etc/MaximusVpsMx/core/hysteria_auth.py << 'PYEOF'
#!/usr/bin/env python3
import sys
import datetime
import os

DB_PATH = "/etc/MaximusVpsMx/hysteria_users.db"
LOG_PATH = "/var/log/MaximusVpsMx/hysteria_auth.log"

def log_msg(msg):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
    except:
        pass

def check_auth():
    try:
        if len(sys.argv) < 3:
            log_msg("Faltan argumentos pasados por Hysteria.")
            sys.exit(1)
            
        client_auth = sys.argv[2].strip()
        
        if not os.path.exists(DB_PATH):
            log_msg("No se encontro la database de usuarios.")
            sys.exit(1)

        with open(DB_PATH, "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) < 3: continue
                
                user = parts[0]
                password = parts[1]
                expiry_str = parts[2]
                
                if password == client_auth:
                    expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
                    if datetime.datetime.now() <= expiry_date:
                        log_msg(f"Auth OK para usuario: {user}")
                        print(user) 
                        sys.exit(0)
                    else:
                        log_msg(f"Auth Fallida: Cuenta expirada ({user})")
                        sys.exit(1)
                        
        log_msg(f"Auth Fallida: Credenciales invalidas (Pass: {client_auth})")
        sys.exit(1)

    except Exception as e:
        log_msg(f"Error interno: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    check_auth()
PYEOF
chmod +x /etc/MaximusVpsMx/core/hysteria_auth.py
touch /etc/MaximusVpsMx/hysteria_users.db

# Generar certificado auto-firmado para TLS/QUIC
echo -e "${GREEN}[+] Generando certificado SSL para QUIC...${NC}"
openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -sha256 \
    -subj "/CN=bing.com/O=Microsoft/C=US" \
    -keyout "$HY_DIR/hysteria.key" \
    -out "$HY_DIR/hysteria.crt" >/dev/null 2>&1

# Generar configuración YAML (Hysteria v2 Multi-User)
echo -e "${GREEN}[+] Generando configuración con motor de autenticación dinámico...${NC}"
cat > "$HY_DIR/config.yaml" << HYEOF
listen: :$hy_port

tls:
  cert: $HY_DIR/hysteria.crt
  key: $HY_DIR/hysteria.key

auth:
  type: command
  command: /etc/MaximusVpsMx/core/hysteria_auth.py

obfs:
  type: salamander
  salamander:
    password: maximus_obfs_maestra

masquerade:
  type: proxy
  proxy:
    url: https://bing.com
    rewriteHost: true

bandwidth:
  up: 100 mbps
  down: 100 mbps
HYEOF

# Matar procesos previos
fuser -k "$hy_port/udp" 2>/dev/null

# Crear servicio systemd
echo -e "${GREEN}[+] Creando servicio systemd...${NC}"
cat > /etc/systemd/system/hysteria.service << EOF
[Unit]
Description=MaximusVpsMx Hysteria v2 QUIC Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$HY_DIR
ExecStart=${HY_DIR}/hysteria server -c ${HY_DIR}/config.yaml
Restart=always
RestartSec=3
LimitNOFILE=infinity

[Install]
WantedBy=multi-user.target
EOF

# Abrir puerto en firewall local
ufw allow ${hy_range}/udp 2>/dev/null

# EXCLUSIÓN Y PORT-HOPPING NAT
echo -e "${YELLOW}[+] Configurando Port-Hopping (Rango $hy_range -> Interno $hy_port)...${NC}"
# Limpiar previas si las hay
iptables -t nat -D PREROUTING -p udp --dport ${hy_range} -j REDIRECT --to-port ${hy_port} 2>/dev/null
ip6tables -t nat -D PREROUTING -p udp --dport ${hy_range} -j REDIRECT --to-port ${hy_port} 2>/dev/null

iptables -t nat -I PREROUTING -p udp --dport ${hy_range} -j REDIRECT --to-port ${hy_port}
ip6tables -t nat -I PREROUTING -p udp --dport ${hy_range} -j REDIRECT --to-port ${hy_port} 2>/dev/null

# Guardar reglas iptables
if command -v iptables-save > /dev/null; then
    iptables-save > /etc/iptables/rules.v4
fi
# Activar y arrancar
systemctl daemon-reload
systemctl enable --now hysteria 2>/dev/null
systemctl restart hysteria 2>/dev/null

# Verificación
sleep 2
if systemctl is-active --quiet hysteria; then
    echo -e "\n${GREEN}=========================================================${NC}"
    echo -e "${GREEN} ✅ HYSTERIA v2 INSTALADO CORRECTAMENTE${NC}"
    echo -e "${CYAN} Rango Port-Hopping: $hy_range${NC}"
    echo -e "${CYAN} Puerto Nativo:   $hy_port${NC}"
    echo -e "${CYAN} Contraseña:      $hy_pass${NC}"
    echo -e "${CYAN} Mascarada:       bing.com (Anti-DPI)${NC}"
    echo -e "${GREEN}=========================================================${NC}"
    echo -e "${YELLOW} NOTA: Tu enlace será IP:$hy_range${NC}"
else
    echo -e "\n${RED}=========================================================${NC}"
    echo -e "${RED} ⚠️ Hysteria se instaló pero no arrancó correctamente.${NC}"
    echo -e "${YELLOW} Verifica con: systemctl status hysteria${NC}"
    echo -e "${RED}=========================================================${NC}"
fi
sleep 3
