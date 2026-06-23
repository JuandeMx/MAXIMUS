#!/bin/bash
# MaximusVpsMx - SSL + PYTHON (Combo Completo)
# Configura Dropbear + Python WebSocket Proxy + Stunnel4 SSL en un solo paso

RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
NC='\033[0m'

ui_hr() { echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"; }
ui_subhr() { echo -e "${CYAN}───────────────────────────────────────────────────────${NC}"; }
ui_prompt() { echo -ne "${YELLOW}$1${NC}"; }
ui_pause() { read -p "Presiona Enter para continuar..." ; }
ui_header() {
    clear
    ui_hr
    echo -e "${YELLOW}           $1${NC}"
    ui_hr
}

mportas() {
    unset portas
    portas_var=$(lsof -V -i tcp -P -n 2>/dev/null | grep -v "ESTABLISHED" | grep -v "COMMAND" | grep "LISTEN")
    while read -r port; do
        var1=$(echo "$port" | awk '{print $1}')
        var2=$(echo "$port" | awk '{print $9}' | awk -F ":" '{print $2}')
        if [[ -n "$var1" && -n "$var2" ]]; then
            if ! echo -e "$portas" | grep -q "$var1 $var2"; then
                portas+="$var1 $var2\n"
            fi
        fi
    done <<<"$portas_var"
    echo -e "$portas"
}

activar_ssl_python() {
    ui_header "INSTALAR SSL + PYTHON (COMBO COMPLETO)"
    echo -e "${WHITE}Este módulo configura todo de un solo golpe:${NC}"
    echo -e "  ${CYAN}1.${WHITE} Dropbear SSH (si no está activo)${NC}"
    echo -e "  ${CYAN}2.${WHITE} Proxy Python WebSocket (Puerto 80)${NC}"
    echo -e "  ${CYAN}3.${WHITE} SSL/TLS vía Stunnel4 (Puerto 443)${NC}"
    ui_hr

    # ═══════════ PASO 1: PUERTOS ═══════════
    echo -e "\n${YELLOW}═══ PASO 1: CONFIGURACIÓN DE PUERTOS ═══${NC}\n"

    read -p " Puerto Dropbear SSH [442]: " DROPBEAR_PORT
    [ -z "$DROPBEAR_PORT" ] && DROPBEAR_PORT=442

    read -p " Puerto OpenSSH [22]: " SSH_PORT
    [ -z "$SSH_PORT" ] && SSH_PORT=22

    read -p " Puerto Proxy Python (WebSocket) [80]: " PROXY_PORT
    [ -z "$PROXY_PORT" ] && PROXY_PORT=80

    read -p " Puerto SSL (Stunnel4) [443]: " SSL_PORT
    [ -z "$SSL_PORT" ] && SSL_PORT=443

    # ═══════════ PASO 2: ESTADO Y ENCABEZADO ═══════════
    echo ""
    ui_subhr
    echo -e "${YELLOW}═══ PASO 2: TEXTO DE ESTADO Y ENCABEZADO ═══${NC}\n"

    read -p " Texto de Estado [By MAXIMUS | ELITE]: " STATUS_TEXT
    [ -z "$STATUS_TEXT" ] && STATUS_TEXT="By MAXIMUS | ELITE"

    read -p " Código de Encabezado (101, 200, 404, 500) [200]: " STATUS_CODE
    [ -z "$STATUS_CODE" ] && STATUS_CODE=200

    # ═══════════ RESUMEN ═══════════
    ui_hr
    echo -e "${YELLOW}           RESUMEN DE CONFIGURACIÓN${NC}"
    ui_hr
    echo -e "  ${WHITE}Dropbear SSH:     ${GREEN}Puerto $DROPBEAR_PORT${NC}"
    echo -e "  ${WHITE}OpenSSH:          ${GREEN}Puerto $SSH_PORT${NC}"
    echo -e "  ${WHITE}Proxy Python WS:  ${GREEN}Puerto $PROXY_PORT -> 127.0.0.1:$DROPBEAR_PORT${NC}"
    echo -e "  ${WHITE}SSL Stunnel4:     ${GREEN}Puerto $SSL_PORT -> 127.0.0.1:$PROXY_PORT${NC}"
    echo -e "  ${WHITE}Texto de Estado:  ${GREEN}$STATUS_TEXT${NC}"
    echo -e "  ${WHITE}Código Respuesta: ${GREEN}$STATUS_CODE${NC}"
    ui_hr
    read -p " ¿Deseas continuar con esta configuración? [s/n]: " confirmar
    if [[ "$confirmar" != "s" && "$confirmar" != "S" && "$confirmar" != "" ]]; then
        echo -e "${RED}❌ Instalación cancelada.${NC}"
        ui_pause
        return 1
    fi

    # ═══════════ PASO 3: INSTALAR DROPBEAR ═══════════
    ui_hr
    echo -e "${YELLOW}[1/3] Configurando Dropbear SSH en puerto $DROPBEAR_PORT...${NC}"
    
    if ! systemctl is-active --quiet dropbear 2>/dev/null; then
        # Instalar Dropbear si no está activo
        DEBIAN_FRONTEND=noninteractive apt-get install -y dropbear >/dev/null 2>&1
    fi

    mkdir -p /etc/dropbear
    touch /etc/dropbear/banner
    
    cat <<EOF >/etc/default/dropbear
NO_START=0
DROPBEAR_EXTRA_ARGS="-p $DROPBEAR_PORT"
DROPBEAR_BANNER="/etc/dropbear/banner"
DROPBEAR_RECEIVE_WINDOW=65536
EOF

    grep -q "^/bin/false" /etc/shells || echo "/bin/false" >>/etc/shells
    
    dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key >/dev/null 2>&1
    dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key >/dev/null 2>&1
    
    systemctl stop dropbear.socket >/dev/null 2>&1 || true
    systemctl disable dropbear.socket >/dev/null 2>&1 || true
    systemctl mask dropbear.socket >/dev/null 2>&1 || true
    rm -f /etc/systemd/system/dropbear.service.d/override.conf 2>/dev/null
    
    ufw allow $DROPBEAR_PORT/tcp >/dev/null 2>&1
    systemctl daemon-reload
    systemctl enable dropbear >/dev/null 2>&1
    systemctl restart dropbear >/dev/null 2>&1
    
    if systemctl is-active --quiet dropbear; then
        echo -e "${GREEN}  ✓ Dropbear ACTIVO en puerto $DROPBEAR_PORT${NC}"
    else
        echo -e "${RED}  ❌ Error al iniciar Dropbear${NC}"
    fi

    # ═══════════ PASO 4: PROXY PYTHON WEBSOCKET ═══════════
    echo -e "\n${YELLOW}[2/3] Configurando Proxy Python WebSocket en puerto $PROXY_PORT...${NC}"
    
    # Matar proxy previo en ese puerto si existiera
    fuser -k $PROXY_PORT/tcp >/dev/null 2>&1
    sleep 1

    # Generar script Python dinámico
    mkdir -p /etc/MaximusVpsMx/core
    cat <<PYEOF >/etc/MaximusVpsMx/core/PDirect-${PROXY_PORT}.py
# -*- coding: utf-8 -*-
import socket, threading, select, sys, time, getopt

LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = '${PROXY_PORT}'
BUFLEN = 16384
TIMEOUT = 60
DEFAULT_HOST = '127.0.0.1:${DROPBEAR_PORT}'
RESPONSE = 'HTTP/1.1 ${STATUS_CODE} <strong>${STATUS_TEXT}</strong>\r\nContent-length: 0\r\n\r\nHTTP/1.1 ${STATUS_CODE} Connection established\r\n\r\n'

class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.running = False
        self.host = host
        self.port = port
        self.threads = []
        self.threadsLock = threading.Lock()
        self.logLock = threading.Lock()

    def run(self):
        self.soc = socket.socket(socket.AF_INET)
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.settimeout(2)
        self.soc.bind((self.host, int(self.port)))
        self.soc.listen(100)
        self.running = True
        try:
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                except socket.timeout:
                    continue
                conn = ConnectionHandler(c, self, addr)
                conn.start()
                self.addConn(conn)
        finally:
            self.running = False
            self.soc.close()

    def addConn(self, conn):
        self.threadsLock.acquire()
        if self.running:
            self.threads.append(conn)
        self.threadsLock.release()

    def removeConn(self, conn):
        self.threadsLock.acquire()
        if conn in self.threads:
            self.threads.remove(conn)
        self.threadsLock.release()

    def close(self):
        self.running = False
        self.threadsLock.acquire()
        for c in list(self.threads):
            c.close()
        self.threadsLock.release()

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient, server, addr):
        threading.Thread.__init__(self)
        self.clientClosed = False
        self.targetClosed = True
        self.client = socClient
        self.server = server

    def close(self):
        try:
            if not self.clientClosed:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
        except: pass
        self.clientClosed = True
        try:
            if not self.targetClosed:
                self.target.shutdown(socket.SHUT_RDWR)
                self.target.close()
        except: pass
        self.targetClosed = True

    def run(self):
        try:
            self.client_buffer = self.client.recv(BUFLEN)
            hostPort = self.findHeader(self.client_buffer, 'X-Real-Host')
            if hostPort == '':
                hostPort = DEFAULT_HOST
            
            if hostPort != '':
                self.method_CONNECT(hostPort)
            else:
                self.client.send('HTTP/1.1 400 NoXRealHost!\r\n\r\n')
        except:
            pass
        finally:
            self.close()
            self.server.removeConn(self)

    def findHeader(self, head, header):
        aux = head.find(header + ': ')
        if aux == -1: return ''
        aux = head.find(':', aux)
        head = head[aux+2:]
        aux = head.find('\r\n')
        if aux == -1: return ''
        return head[:aux]

    def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = ${DROPBEAR_PORT}
        soc_family, soc_type, proto, _, address = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family, soc_type, proto)
        self.targetClosed = False
        self.target.connect(address)

    def method_CONNECT(self, path):
        self.connect_target(path)
        self.client.sendall(RESPONSE)
        self.doCONNECT()

    def doCONNECT(self):
        socs = [self.client, self.target]
        count = 0
        error = False
        while True:
            count += 1
            recv, _, err = select.select(socs, [], socs, 3)
            if err: error = True
            if recv:
                for in_ in recv:
                    try:
                        data = in_.recv(BUFLEN)
                        if data:
                            if in_ is self.target:
                                self.client.send(data)
                            else:
                                while data:
                                    byte = self.target.send(data)
                                    data = data[byte:]
                            count = 0
                        else:
                            break
                    except:
                        error = True
                        break
            if count == TIMEOUT: error = True
            if error: break

if __name__ == '__main__':
    server = Server(LISTENING_ADDR, int(LISTENING_PORT))
    server.start()
    while True:
        try: time.sleep(2)
        except KeyboardInterrupt:
            server.close()
            break
PYEOF

    chmod +x /etc/MaximusVpsMx/core/PDirect-${PROXY_PORT}.py
    ufw allow ${PROXY_PORT}/tcp >/dev/null 2>&1
    
    # Ejecutar en screen
    screen -dmS pydic-${PROXY_PORT} python3 /etc/MaximusVpsMx/core/PDirect-${PROXY_PORT}.py 2>/dev/null
    echo "${PROXY_PORT}" >> /etc/MaximusVpsMx/core/PDirect.log
    
    sleep 1
    if ps aux | grep -v grep | grep -q "PDirect-${PROXY_PORT}"; then
        echo -e "${GREEN}  ✓ Proxy Python WS ACTIVO en puerto $PROXY_PORT -> Dropbear $DROPBEAR_PORT${NC}"
    else
        echo -e "${RED}  ❌ Error al iniciar el proxy Python${NC}"
    fi

    # ═══════════ PASO 5: SSL STUNNEL4 ═══════════
    echo -e "\n${YELLOW}[3/3] Configurando SSL (Stunnel4) en puerto $SSL_PORT...${NC}"
    
    DEBIAN_FRONTEND=noninteractive apt-get install -y stunnel4 openssl >/dev/null 2>&1
    
    mkdir -p /etc/stunnel
    cat <<EOF >/etc/stunnel/stunnel.conf
client = no
[SSL]
cert = /etc/stunnel/stunnel.pem
accept = ${SSL_PORT}
connect = 127.0.0.1:${PROXY_PORT}
EOF

    # Generar certificado auto-firmado si no existe
    if [[ ! -f /etc/stunnel/stunnel.pem ]]; then
        echo -e "${YELLOW}  [+] Generando certificado SSL auto-firmado...${NC}"
        openssl genrsa -out /etc/stunnel/stunnel.key 2048 >/dev/null 2>&1
        (echo "MX" ; echo "Mexico" ; echo "CDMX" ; echo "Maximus" ; echo "Elite" ; echo "MaximusElite" ; echo "admin@maximus.com" ) | openssl req -new -key /etc/stunnel/stunnel.key -x509 -days 1000 -out /etc/stunnel/stunnel.crt >/dev/null 2>&1
        cat /etc/stunnel/stunnel.crt /etc/stunnel/stunnel.key > /etc/stunnel/stunnel.pem
        rm -f /etc/stunnel/stunnel.crt /etc/stunnel/stunnel.key
    fi
    
    sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4 2>/dev/null
    echo "ENABLED=1" >>/etc/default/stunnel4
    
    ufw allow ${SSL_PORT}/tcp >/dev/null 2>&1
    systemctl daemon-reload
    systemctl enable stunnel4 >/dev/null 2>&1
    systemctl restart stunnel4 >/dev/null 2>&1
    
    if systemctl is-active --quiet stunnel4; then
        echo -e "${GREEN}  ✓ SSL Stunnel4 ACTIVO en puerto $SSL_PORT -> Proxy Python $PROXY_PORT${NC}"
    else
        echo -e "${RED}  ❌ Error al iniciar Stunnel4${NC}"
    fi

    # ═══════════ RESULTADO FINAL ═══════════
    SERVER_IP=$(wget -qO- ipv4.icanhazip.com 2>/dev/null)
    [ -z "$SERVER_IP" ] && SERVER_IP="TU_IP"

    echo ""
    ui_hr
    echo -e "${GREEN}       ✅ SSL + PYTHON INSTALADO CON ÉXITO${NC}"
    ui_hr
    echo -e ""
    echo -e "  ${YELLOW}📋 CADENA DE CONEXIÓN:${NC}"
    echo -e "  ${WHITE}Cliente -> ${CYAN}SSL:$SSL_PORT${WHITE} -> ${CYAN}Python:$PROXY_PORT${WHITE} -> ${CYAN}Dropbear:$DROPBEAR_PORT${NC}"
    echo -e ""
    echo -e "  ${YELLOW}📋 CONFIGURACIÓN PARA HTTP CUSTOM:${NC}"
    echo -e "  ${WHITE}IP/Host:  ${GREEN}$SERVER_IP${NC}"
    echo -e "  ${WHITE}SSH Port: ${GREEN}$DROPBEAR_PORT${NC}"
    echo -e "  ${WHITE}SSL Port: ${GREEN}$SSL_PORT${NC}"
    echo -e "  ${WHITE}WS Port:  ${GREEN}$PROXY_PORT${NC}"
    ui_hr
    ui_pause
}

desactivar_ssl_python() {
    ui_header "DESINSTALAR SSL + PYTHON"
    echo -e "${YELLOW}[+] Deteniendo todos los componentes...${NC}"
    
    # Detener proxies Python
    for pid in $(ps aux | grep 'PDirect-' | grep -v grep | awk '{print $2}'); do
        kill -9 "$pid" 2>/dev/null
    done
    screen -wipe >/dev/null 2>&1
    rm -f /etc/MaximusVpsMx/core/PDirect-*.py
    rm -f /etc/MaximusVpsMx/core/PDirect.log
    
    # Detener Stunnel
    systemctl stop stunnel4 >/dev/null 2>&1
    systemctl disable stunnel4 >/dev/null 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get purge stunnel4 -y >/dev/null 2>&1
    rm -rf /etc/stunnel/* >/dev/null 2>&1
    
    # Detener Dropbear
    systemctl stop dropbear >/dev/null 2>&1
    systemctl disable dropbear >/dev/null 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get purge dropbear -y >/dev/null 2>&1
    rm -f /etc/default/dropbear 2>/dev/null
    
    ui_hr
    echo -e "${GREEN}✓ SSL + PYTHON DESINSTALADO COMPLETAMENTE${NC}"
    ui_pause
}

while true; do
    ui_header "SSL + PYTHON (COMBO COMPLETO)"
    
    # Status
    systemctl is-active --quiet dropbear 2>/dev/null && st_drop="${GREEN}[ ACTIVO ]${NC}" || st_drop="${RED}[ OFF ]${NC}"
    ps aux | grep -v grep | grep -q "PDirect-" && st_py="${GREEN}[ ACTIVO ]${NC}" || st_py="${RED}[ OFF ]${NC}"
    systemctl is-active --quiet stunnel4 2>/dev/null && st_ssl="${GREEN}[ ACTIVO ]${NC}" || st_ssl="${RED}[ OFF ]${NC}"
    
    echo -e "  ${WHITE}Estado Actual:${NC}"
    echo -e "    ${WHITE}Dropbear SSH:    $st_drop"
    echo -e "    ${WHITE}Proxy Python WS: $st_py"
    echo -e "    ${WHITE}SSL Stunnel4:    $st_ssl"
    ui_hr
    echo -e "  ${CYAN}[1]>${WHITE} INSTALAR / CONFIGURAR SSL + PYTHON${NC}"
    echo -e "  ${CYAN}[2]>${WHITE} DESINSTALAR SSL + PYTHON${NC}"
    ui_hr
    echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
    ui_hr
    ui_prompt "Selecciona una opción: "
    read -r opcao
    
    case $opcao in
        1) activar_ssl_python ;;
        2) desactivar_ssl_python ;;
        0) break ;;
        *) continue ;;
    esac
done
