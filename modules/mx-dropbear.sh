#!/bin/bash
# MaximusVpsMx - Dropbear Manager
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

activar_dropbear() {
    ui_header "INSTALAR / CONFIGURAR DROPBEAR"
    
    echo -e "${WHITE}Puedes activar varios puertos de forma secuencial (separados por espacio)${NC}"
    echo -e "Ejemplo: ${GREEN}22 44 80 443${NC}\n"
    
    read -p "Digite los Puertos: " -e -i "442 444" DPORT
    
    TTOTAL2=($DPORT)
    PORT2=""
    for ((i = 0; i < ${#TTOTAL2[@]}; i++)); do
        if [[ -z "$(mportas | grep -w "${TTOTAL2[$i]}")" ]]; then
            echo -e "${YELLOW}▶ Puerto Elegido: ${GREEN}${TTOTAL2[$i]} OK${NC}"
            PORT2="$PORT2 ${TTOTAL2[$i]}"
        else
            # Permitir si ya es dropbear el que lo tiene abierto
            if mportas | grep -q "dropbear ${TTOTAL2[$i]}"; then
                echo -e "${YELLOW}▶ Puerto Elegido: ${GREEN}${TTOTAL2[$i]} OK (Ya es Dropbear)${NC}"
                PORT2="$PORT2 ${TTOTAL2[$i]}"
            else
                echo -e "${YELLOW}▶ Puerto Elegido: ${RED}${TTOTAL2[$i]} FAIL (En Uso)${NC}"
            fi
        fi
    done
    
    if [[ -z "$PORT2" ]]; then
        echo -e "${RED}❌ Ningún puerto válido fue elegido.${NC}"
        ui_pause
        return 1
    fi
    
    ui_hr
    echo -e "${YELLOW}[+] Instalando dependencias de Dropbear...${NC}"
    DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get install dropbear -y >/dev/null 2>&1
    
    echo -e "${YELLOW}[+] Compilando Dropbear desde código fuente para compatibilidad con HTTP Custom...${NC}"
    mkdir -p /var/log/MaximusVpsMx
    echo "=== Iniciando compilación de Dropbear ===" > /var/log/MaximusVpsMx/dropbear_compile.log

    DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential zlib1g-dev wget bzip2 >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1

    cd /tmp
    rm -rf dropbear-2025.89*
    if wget -q https://matt.ucc.asn.au/dropbear/releases/dropbear-2025.89.tar.bz2 || wget -q https://dropbear.nl/mirror/releases/dropbear-2025.89.tar.bz2; then
        tar -xf dropbear-2025.89.tar.bz2 >> /var/log/MaximusVpsMx/dropbear_compile.log 2>&1
        cd dropbear-2025.89
        
        # Escribir localoptions.h para habilitar todos los algoritmos antiguos
        cat <<EOF > localoptions.h
#define DROPBEAR_DH_GROUP1 1
#define DROPBEAR_DH_GROUP1_SHA1 1
#define DROPBEAR_DH_GROUP14 1
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
            echo -e "${GREEN}✓ Dropbear optimizado y compilado exitosamente.${NC}"
        else
            echo -e "${RED}❌ Error al compilar. Se usará el binario predeterminado del sistema.${NC}"
            echo -e "${YELLOW}--- DETALLE DEL ERROR DE COMPILACIÓN (Últimas 20 líneas) ---${NC}"
            tail -n 20 /var/log/MaximusVpsMx/dropbear_compile.log
        fi
    else
        echo -e "${RED}❌ No se pudo descargar el código fuente. Se usará el binario predeterminado del sistema.${NC}"
    fi
    cd /tmp

    mkdir -p /etc/dropbear
    touch /etc/dropbear/banner
    
    # Escribir configuración
    cat <<EOF >/etc/default/dropbear
NO_START=0
DROPBEAR_EXTRA_ARGS="VAR"
DROPBEAR_BANNER="/etc/dropbear/banner"
DROPBEAR_RECEIVE_WINDOW=65536
EOF

    # Reemplazar argumentos con los puertos correspondientes
    for dpts in $PORT2; do
        sed -i "s/VAR/-p $dpts VAR/g" /etc/default/dropbear
    done
    sed -i "s/VAR//g" /etc/default/dropbear
    
    # Agregar shell falso si no existe
    grep -q "^/bin/false" /etc/shells || echo "/bin/false" >>/etc/shells
    
    # Generar host keys
    dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key >/dev/null 2>&1
    dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key >/dev/null 2>&1
    
    # Desactivar socket mode (Ubuntu 24.04 mitigación)
    systemctl stop dropbear.socket >/dev/null 2>&1 || true
    systemctl disable dropbear.socket >/dev/null 2>&1 || true
    systemctl mask dropbear.socket >/dev/null 2>&1 || true
    rm -f /etc/systemd/system/dropbear.service.d/override.conf 2>/dev/null
    
    # Abrir puertos en el firewall
    for dpts in $PORT2; do
        ufw allow $dpts/tcp >/dev/null 2>&1
    done
    
    # Reiniciar servicios
    systemctl daemon-reload
    service ssh restart >/dev/null 2>&1
    
    # Encender Dropbear
    sed -i "s/NO_START=1/NO_START=0/g" /etc/default/dropbear 2>/dev/null
    systemctl enable dropbear >/dev/null 2>&1
    systemctl restart dropbear >/dev/null 2>&1
    
    ui_hr
    echo -e "${GREEN}✓ DROPBEAR INSTALADO/CONFIGURADO CON ÉXITO EN PUERTOS: $PORT2${NC}"
    ui_pause
}

desactivar_dropbear() {
    ui_header "DESINSTALAR DROPBEAR"
    echo -e "${YELLOW}[+] Deteniendo Dropbear...${NC}"
    systemctl stop dropbear >/dev/null 2>&1
    systemctl disable dropbear >/dev/null 2>&1
    
    echo -e "${YELLOW}[+] Eliminando paquetes de Dropbear...${NC}"
    DEBIAN_FRONTEND=noninteractive apt-get remove --purge dropbear -y >/dev/null 2>&1
    killall -9 dropbear >/dev/null 2>&1
    rm -rf /etc/dropbear/* >/dev/null 2>&1
    rm -f /etc/default/dropbear 2>/dev/null
    
    ui_hr
    echo -e "${GREEN}✓ DROPBEAR DESINSTALADO CON ÉXITO${NC}"
    ui_pause
}

while true; do
    ui_header "DROPBEAR MANAGER"
    echo -e "  ${CYAN}[1]>${WHITE} INSTALAR / CONFIGURAR DROPBEAR${NC}"
    echo -e "  ${CYAN}[2]>${WHITE} DESINSTALAR DROPBEAR${NC}"
    ui_hr
    echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
    ui_hr
    ui_prompt "Selecciona una opción: "
    read -r opcao
    
    case $opcao in
        1) activar_dropbear ;;
        2) desactivar_dropbear ;;
        0) break ;;
        *) continue ;;
    esac
done
