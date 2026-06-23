#!/bin/bash
# MaximusVpsMx - Python Proxies & Tunnels Manager
# Adapta la lógica de Chumo LATAM a la estética de Maximus

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

# Obtiene la lista de puertos en uso
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

get_public_ip() {
    local ip
    ip=$(wget -qO- ipv4.icanhazip.com 2>/dev/null)
    [ -z "$ip" ] && ip=$(curl -fsSL https://api.ipify.org 2>/dev/null)
    [ -z "$ip" ] && ip="127.0.0.1"
    echo "$ip"
}

# --- 12) WEBSOCKET STATUS EDITABLE ---
ws_editable() {
    activar_ws() {
        ui_header "ACTIVAR PROXY WEBSOCKET EDITABLE"
        while true; do
            read -p "Digite el Puerto para el Websocket: " -e -i "8081" porta_socket
            if ! mportas | grep -q -w "$porta_socket"; then
                break
            else
                echo -e "${RED}❌ Puerto ya en uso. Elige otro.${NC}"
            fi
        done
        
        read -p "Introduzca el texto de estado (HTML permitido): " -e -i "By SCRIPT | LATAM" texto_soket
        read -p "Digite puerto local de anclaje (ej: SSH 22 / Dropbear 44): " -e -i "444" puetoantla
        read -p "Estatus de encabezado (101, 200, 404, 500): " -e -i "200" rescabeza
        
        ui_hr
        echo -e "${YELLOW}[+] Generando y configurando proxy WebSocket...${NC}"
        
        # Escribir script Python dinámico
        cat <<EOF >/etc/MaximusVpsMx/core/PDirect-${porta_socket}.py
# -*- coding: utf-8 -*-
import socket, threading, select, sys, time, getopt

LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = '${porta_socket}'
BUFLEN = 16384
TIMEOUT = 60
DEFAULT_HOST = '127.0.0.1:${puetoantla}'
RESPONSE = 'HTTP/1.1 ${rescabeza} <strong>${texto_soket}</strong>\r\nContent-length: 0\r\n\r\nHTTP/1.1 ${rescabeza} Connection established\r\n\r\n'

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
        self.client_buffer = b''
        self.server = server
        self.method = 'CONNECT'

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
                self.client.send(b'HTTP/1.1 400 NoXRealHost!\r\n\r\n')
        except:
            pass
        finally:
            self.close()
            self.server.removeConn(self)

    def findHeader(self, head, header):
        try:
            if isinstance(head, bytes):
                head = head.decode('utf-8', errors='ignore')
            aux = head.find(header + ': ')
            if aux == -1: return ''
            aux = head.find(':', aux)
            head = head[aux+2:]
            aux = head.find('\r\n')
            if aux == -1: return ''
            return head[:aux]
        except:
            return ''

    def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = ${puetoantla}
        soc_family, soc_type, proto, _, address = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family, soc_type, proto)
        self.targetClosed = False
        self.target.connect(address)

    def method_CONNECT(self, path):
        self.connect_target(path)
        self.client.sendall(RESPONSE.encode('utf-8'))
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
EOF

        chmod +x /etc/MaximusVpsMx/core/PDirect-${porta_socket}.py
        ufw allow ${porta_socket}/tcp >/dev/null 2>&1
        
        # Ejecutar
        screen -dmS pydic-${porta_socket} python /etc/MaximusVpsMx/core/PDirect-${porta_socket}.py 2>/dev/null || screen -dmS pydic-${porta_socket} python3 /etc/MaximusVpsMx/core/PDirect-${porta_socket}.py 2>/dev/null
        
        echo "${porta_socket}" >> /etc/MaximusVpsMx/core/PDirect.log
        
        echo -e "${GREEN}✓ PROXY WEBSOCKET ACTIVO EN PUERTO: $porta_socket${NC}"
        ui_pause
    }

    desactivar_ws() {
        ui_header "DESACTIVAR PROXY WEBSOCKET"
        log_file="/etc/MaximusVpsMx/core/PDirect.log"
        if [[ ! -s "$log_file" ]]; then
            echo -e "${RED}❌ No hay puertos WebSocket registrados activos.${NC}"
            ui_pause
            return 1
        fi
        
        echo -e "${WHITE}Puertos WebSocket Activos:${NC}"
        ui_subhr
        cat "$log_file"
        ui_subhr
        
        read -p "Digite el puerto a desactivar: " portselect
        screen -S pydic-${portselect} -p 0 -X quit >/dev/null 2>&1
        rm -f /etc/MaximusVpsMx/core/PDirect-${portselect}.py
        sed -i "/^${portselect}$/d" "$log_file"
        
        echo -e "${GREEN}✓ Proxy WebSocket en puerto $portselect detenido.${NC}"
        ui_pause
    }

    while true; do
        ui_header "WEBSOCKET STATUS EDITABLE"
        echo -e "  ${CYAN}[1]>${WHITE} ACTIVAR NUEVO PROXY WEBSOCKET${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} DETENER UN PROXY WEBSOCKET${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
        ui_hr
        ui_prompt "Selecciona: "
        read -r opt
        case $opt in
            1) activar_ws ;;
            2) desactivar_ws ;;
            0) break ;;
        esac
    done
}

# --- 13) PROXY OPENVPN ---
proxy_openvpn() {
    activar_popen() {
        ui_header "ACTIVAR PROXY OPENVPN (PYTHON)"
        while true; do
            read -p "Digite el Puerto para el Proxy OpenVPN: " -e -i "8081" porta_socket
            if ! mportas | grep -q -w "$porta_socket"; then
                break
            else
                echo -e "${RED}❌ Puerto ya en uso. Elige otro.${NC}"
            fi
        done
        
        read -p "Introduzca el texto de estado: " -e -i "By SCRIPT | LATAM" texto_soket
        
        ufw allow ${porta_socket}/tcp >/dev/null 2>&1
        
        # Iniciar backend
        screen -dmS popenvpn-${porta_socket} python /etc/MaximusVpsMx/core/POpen.py "$porta_socket" "$texto_soket" 2>/dev/null || screen -dmS popenvpn-${porta_socket} python3 /etc/MaximusVpsMx/core/POpen.py "$porta_socket" "$texto_soket" 2>/dev/null
        
        echo "${porta_socket}" >> /etc/MaximusVpsMx/core/POpen.log
        
        ui_hr
        echo -e "${GREEN}✓ PROXY OPENVPN ACTIVO EN PUERTO: $porta_socket${NC}"
        ui_pause
    }

    desactivar_popen() {
        ui_header "DESACTIVAR PROXY OPENVPN"
        # Detener screens
        killall -9 POpen.py >/dev/null 2>&1
        for pid in $(ps aux | grep 'POpen.py' | grep -v grep | awk '{print $2}'); do
            kill -9 "$pid" 2>/dev/null
        done
        screen -wipe >/dev/null 2>&1
        rm -f /etc/MaximusVpsMx/core/POpen.log
        
        echo -e "${GREEN}✓ Todos los Proxies OpenVPN detenidos.${NC}"
        ui_pause
    }

    while true; do
        ui_header "PROXY OPENVPN (PYTHON)"
        echo -e "  ${CYAN}[1]>${WHITE} ACTIVAR PROXY OPENVPN${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} DETENER TODOS LOS PROXIES OPENVPN${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
        ui_hr
        ui_prompt "Selecciona: "
        read -r opt
        case $opt in
            1) activar_popen ;;
            2) desactivar_popen ;;
            0) break ;;
        esac
    done
}

# --- 14) PROXY PUBLICO ---
proxy_publico() {
    activar_ppub() {
        ui_header "ACTIVAR PROXY PÚBLICO (PYTHON)"
        while true; do
            read -p "Digite el Puerto para el Proxy Público: " -e -i "8082" porta_socket
            if ! mportas | grep -q -w "$porta_socket"; then
                break
            else
                echo -e "${RED}❌ Puerto ya en uso. Elige otro.${NC}"
            fi
        done
        
        read -p "Introduzca el texto de estado: " -e -i "By SCRIPT | LATAM" texto_soket
        
        ufw allow ${porta_socket}/tcp >/dev/null 2>&1
        
        # Iniciar backend
        screen -dmS ppublico-${porta_socket} python /etc/MaximusVpsMx/core/PPub.py "$porta_socket" "$texto_soket" 2>/dev/null || screen -dmS ppublico-${porta_socket} python3 /etc/MaximusVpsMx/core/PPub.py "$porta_socket" "$texto_soket" 2>/dev/null
        
        echo "${porta_socket}" >> /etc/MaximusVpsMx/core/PPub.log
        
        ui_hr
        echo -e "${GREEN}✓ PROXY PÚBLICO ACTIVO EN PUERTO: $porta_socket${NC}"
        ui_pause
    }

    desactivar_ppub() {
        ui_header "DESACTIVAR PROXY PÚBLICO"
        killall -9 PPub.py >/dev/null 2>&1
        for pid in $(ps aux | grep 'PPub.py' | grep -v grep | awk '{print $2}'); do
            kill -9 "$pid" 2>/dev/null
        done
        screen -wipe >/dev/null 2>&1
        rm -f /etc/MaximusVpsMx/core/PPub.log
        
        echo -e "${GREEN}✓ Todos los Proxies Públicos detenidos.${NC}"
        ui_pause
    }

    while true; do
        ui_header "PROXY PUBLICO (PYTHON)"
        echo -e "  ${CYAN}[1]>${WHITE} ACTIVAR PROXY PÚBLICO${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} DETENER TODOS LOS PROXIES PÚBLICOS${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
        ui_hr
        ui_prompt "Selecciona: "
        read -r opt
        case $opt in
            1) activar_ppub ;;
            2) desactivar_ppub ;;
            0) break ;;
        esac
    done
}

# --- 15) PROXY PRIVADO ---
proxy_privado() {
    activar_ppriv() {
        ui_header "ACTIVAR PROXY PRIVADO (PYTHON)"
        while true; do
            read -p "Digite el Puerto para el Proxy Privado: " -e -i "8083" porta_socket
            if ! mportas | grep -q -w "$porta_socket"; then
                break
            else
                echo -e "${RED}❌ Puerto ya en uso. Elige otro.${NC}"
            fi
        done
        
        read -p "Introduzca el texto de estado: " -e -i "By SCRIPT | LATAM" texto_soket
        
        local_ip=$(get_public_ip)
        ufw allow ${porta_socket}/tcp >/dev/null 2>&1
        
        # Iniciar backend (PPriv usa python3)
        screen -dmS pprivado-${porta_socket} python3 /etc/MaximusVpsMx/core/PPriv.py "$porta_socket" "$texto_soket" "$local_ip"
        
        echo "${porta_socket}" >> /etc/MaximusVpsMx/core/PPriv.log
        
        ui_hr
        echo -e "${GREEN}✓ PROXY PRIVADO ACTIVO EN PUERTO: $porta_socket${NC}"
        ui_pause
    }

    desactivar_ppriv() {
        ui_header "DESACTIVAR PROXY PRIVADO"
        killall -9 PPriv.py >/dev/null 2>&1
        for pid in $(ps aux | grep 'PPriv.py' | grep -v grep | awk '{print $2}'); do
            kill -9 "$pid" 2>/dev/null
        done
        screen -wipe >/dev/null 2>&1
        rm -f /etc/MaximusVpsMx/core/PPriv.log
        
        echo -e "${GREEN}✓ Todos los Proxies Privados detenidos.${NC}"
        ui_pause
    }

    while true; do
        ui_header "PROXY PRIVADO (PYTHON)"
        echo -e "  ${CYAN}[1]>${WHITE} ACTIVAR PROXY PRIVADO${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} DETENER TODOS LOS PROXIES PRIVADOS${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
        ui_hr
        ui_prompt "Selecciona: "
        read -r opt
        case $opt in
            1) activar_ppriv ;;
            2) desactivar_ppriv ;;
            0) break ;;
        esac
    done
}

# --- 9) GETTUNEL ---
get_tunnel() {
    activar_get() {
        ui_header "ACTIVAR PROXY GETTUNEL"
        while true; do
            read -p "Digite el Puerto para GETTUNEL: " -e -i "8085" porta_socket
            if ! mportas | grep -q -w "$porta_socket"; then
                break
            else
                echo -e "${RED}❌ Puerto ya en uso. Elige otro.${NC}"
            fi
        done
        
        read -p "Digite la contraseña del proxy: " -e -i "SCRIP-LATAM" passg
        echo "$passg" > /etc/MaximusVpsMx/core/pwd.pwd
        
        ufw allow ${porta_socket}/tcp >/dev/null 2>&1
        
        # Iniciar backend
        screen -dmS getpy python /etc/MaximusVpsMx/core/PGet.py -b "0.0.0.0:$porta_socket" -p "/etc/MaximusVpsMx/core/pwd.pwd" 2>/dev/null || screen -dmS getpy python3 /etc/MaximusVpsMx/core/PGet.py -b "0.0.0.0:$porta_socket" -p "/etc/MaximusVpsMx/core/pwd.pwd" 2>/dev/null
        
        ui_hr
        echo -e "${GREEN}✓ GETTUNEL ACTIVO EN PUERTO: $porta_socket${NC}"
        ui_pause
    }

    desactivar_get() {
        ui_header "DESACTIVAR PROXY GETTUNEL"
        killall -9 PGet.py >/dev/null 2>&1
        for pid in $(ps aux | grep 'PGet.py' | grep -v grep | awk '{print $2}'); do
            kill -9 "$pid" 2>/dev/null
        done
        screen -wipe >/dev/null 2>&1
        rm -f /etc/MaximusVpsMx/core/pwd.pwd
        
        echo -e "${GREEN}✓ GETTUNEL detenido con éxito.${NC}"
        ui_pause
    }

    while true; do
        ui_header "GETTUNEL PROXY"
        echo -e "  ${CYAN}[1]>${WHITE} ACTIVAR GETTUNEL${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} DETENER GETTUNEL${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
        ui_hr
        ui_prompt "Selecciona: "
        read -r opt
        case $opt in
            1) activar_get ;;
            2) desactivar_get ;;
            0) break ;;
        esac
    done
}

# --- 10) TCP-OVER ---
tcp_over() {
    activar_tcp() {
        ui_header "ACTIVAR PROXY TCP-OVER"
        while true; do
            read -p "Digite el Puerto para TCP-OVER: " -e -i "8888" porta_socket
            if ! mportas | grep -q -w "$porta_socket"; then
                break
            else
                echo -e "${RED}❌ Puerto ya en uso. Elige otro.${NC}"
            fi
        done
        
        read -p "Digite banner del proxy: " -e -i "SCRIP-LATAM" passg
        
        # Comprobar e instalar sckt/scktcheck binaries
        if [[ ! -f /usr/sbin/sckt || ! -f /bin/scktcheck ]]; then
            echo -e "${YELLOW}[+] Descargando binarios de TCP-OVER...${NC}"
            rm -rf /tmp/socks_over 2>/dev/null
            mkdir -p /tmp/socks_over
            wget -qO /tmp/socks_over/backsocz.zip "https://raw.githubusercontent.com/NetVPS/LATAM_Oficial/main/Ejecutables/backsocz.zip"
            cd /tmp/socks_over || exit
            unzip -o backsocz.zip >/dev/null 2>&1
            
            # Copiar configs de ssh
            cp -f backsocz/ssh /etc/ssh/sshd_config >/dev/null 2>&1
            service ssh restart >/dev/null 2>&1
            
            py_ver=$(python3 --version | awk '{print $2}' | cut -d'.' -f1,2)
            if [[ -f "backsocz/sckt${py_ver}" ]]; then
                cp -f "backsocz/sckt${py_ver}" /usr/sbin/sckt
            else
                # Fallback al binario de python más alto si no coincide exactamente
                cp -f backsocz/sckt3.8 /usr/sbin/sckt 2>/dev/null || cp -f backsocz/sckt3.6 /usr/sbin/sckt 2>/dev/null
            fi
            cp -f backsocz/scktcheck /bin/scktcheck
            
            chmod +x /bin/scktcheck
            chmod +x /usr/sbin/sckt
            cd ~ || exit
            rm -rf /tmp/socks_over
        fi
        
        ufw allow ${porta_socket}/tcp >/dev/null 2>&1
        screen -dmS sokz scktcheck "$porta_socket" "$passg"
        
        ui_hr
        echo -e "${GREEN}✓ PROXY TCP-OVER ACTIVO EN PUERTO: $porta_socket${NC}"
        ui_pause
    }

    desactivar_tcp() {
        ui_header "DESACTIVAR PROXY TCP-OVER"
        killall -9 scktcheck sckt >/dev/null 2>&1
        for pid in $(ps aux | grep -E 'scktcheck|sckt' | grep -v grep | awk '{print $2}'); do
            kill -9 "$pid" 2>/dev/null
        done
        screen -wipe >/dev/null 2>&1
        
        echo -e "${GREEN}✓ TCP-OVER detenido con éxito.${NC}"
        ui_pause
    }

    while true; do
        ui_header "TCP-OVER PROXY"
        echo -e "  ${CYAN}[1]>${WHITE} ACTIVAR TCP-OVER${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} DETENER TCP-OVER${NC}"
        ui_hr
        echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
        ui_hr
        ui_prompt "Selecciona: "
        read -r opt
        case $opt in
            1) activar_tcp ;;
            2) desactivar_tcp ;;
            0) break ;;
        esac
    done
}

# --- MAIN ---
mode=$1
case $mode in
    9) get_tunnel ;;
    10) tcp_over ;;
    12) ws_editable ;;
    13) proxy_openvpn ;;
    14) proxy_publico ;;
    15) proxy_privado ;;
    *) echo -e "${RED}Modo no soportado${NC}" ;;
esac
