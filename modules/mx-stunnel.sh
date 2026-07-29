#!/bin/bash
# MaximusVpsMx - Stunnel4 (SSL/TLS) Manager
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

# Obtiene puertos en uso
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

ssl_stunel() {
    # Si ya está instalado (comprobando existencia del binario), ofrecer opciones
    if [[ -f /usr/bin/stunnel4 || -f /usr/sbin/stunnel4 ]]; then
        ui_header "GESTIÓN SSL (STUNNEL4)"
        echo -e "${YELLOW}Stunnel4 ya está instalado en el sistema.${NC}"
        if [ -f /etc/stunnel/stunnel.conf ]; then
            echo -e "${WHITE}Configuración actual en /etc/stunnel/stunnel.conf:${NC}"
            grep -E 'accept|connect' /etc/stunnel/stunnel.conf 2>/dev/null | sed 's/^/  /'
        fi
        ui_hr
        echo -e "  ${CYAN}[1]>${WHITE} Reconfigurar / Reinstalar SSL Directo${NC}"
        echo -e "  ${CYAN}[2]>${WHITE} Desinstalar SSL (Stunnel4) completamente${NC}"
        echo -e "  ${WHITE}[0]> Cancelar${NC}"
        ui_hr
        read -p "Selecciona una opción: " opt_st
        case $opt_st in
            1)
                ;;
            2)
                ui_header "DESINSTALAR SSL (STUNNEL4)"
                systemctl stop stunnel4 >/dev/null 2>&1
                systemctl disable stunnel4 >/dev/null 2>&1
                killall -9 stunnel4 >/dev/null 2>&1
                pkill -9 stunnel4 >/dev/null 2>&1
                echo -e "${YELLOW}[+] Eliminando stunnel4...${NC}"
                DEBIAN_FRONTEND=noninteractive apt-get purge stunnel4 -y >/dev/null 2>&1
                rm -rf /etc/stunnel/* >/dev/null 2>&1
                systemctl daemon-reload >/dev/null 2>&1
                ui_hr
                echo -e "${GREEN}✓ SSL (STUNNEL4) DESINSTALADO CON ÉXITO${NC}"
                ui_pause
                return 0
                ;;
            *)
                return 0
                ;;
        esac
    fi
    
    ui_header "INSTALAR SSL (STUNNEL4)"
    echo -e "${WHITE}Seleccione un puerto de anclaje activo (SSH/Dropbear/Squid/Websocket)...${NC}"
    ui_hr
    
    while true; do
        read -p "Puerto Local (Ancla): " -e -i "444" portx
        if [[ -n "$portx" ]]; then
            if mportas | grep -q -w "$portx"; then
                break
            else
                echo -e "${RED}❌ Puerto inválido o inactivo. Intente con uno activo.${NC}"
            fi
        fi
    done
    
    ui_hr
    echo -e "${WHITE}Selecciona el puerto público para el servicio SSL/TLS...${NC}"
    while true; do
        read -p "Puerto SSL: " -e -i "443" SSLPORT
        if ! mportas | grep -q -w "$SSLPORT"; then
            break
        else
            echo -e "${RED}❌ Puerto $SSLPORT ya está en uso. Elige otro.${NC}"
        fi
    done
    
    ui_hr
    echo -e "${YELLOW}[+] Instalando Stunnel4...${NC}"
    DEBIAN_FRONTEND=noninteractive apt-get update -y >/dev/null 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get install stunnel4 openssl unzip -y >/dev/null 2>&1
    
    mkdir -p /etc/stunnel
    cat <<EOF >/etc/stunnel/stunnel.conf
client = no
[SSL]
cert = /etc/stunnel/stunnel.pem
accept = ${SSLPORT}
connect = 127.0.0.1:${portx}
EOF

    ui_hr
    echo -e "${YELLOW}[+] Generando Certificado SSL Auto-Firmado...${NC}"
    echo -e "${WHITE}Presione ENTER para dejar los datos por defecto...${NC}\n"
    
    openssl genrsa -out /etc/stunnel/stunnel.key 2048 >/dev/null 2>&1
    (echo "MX" ; echo "Mexico" ; echo "CDMX" ; echo "Maximus" ; echo "Elite" ; echo "MaximusElite" ; echo "admin@maximus.com" ) | openssl req -new -key /etc/stunnel/stunnel.key -x509 -days 1000 -out /etc/stunnel/stunnel.crt >/dev/null 2>&1
    cat /etc/stunnel/stunnel.crt /etc/stunnel/stunnel.key > /etc/stunnel/stunnel.pem
    rm -f /etc/stunnel/stunnel.crt /etc/stunnel/stunnel.key
    
    # Habilitar servicio
    sed -i 's/ENABLED=0/ENABLED=1/g' /etc/default/stunnel4 2>/dev/null
    echo "ENABLED=1" >>/etc/default/stunnel4
    
    # Configurar systemd y arrancar
    ufw allow ${SSLPORT}/tcp >/dev/null 2>&1
    systemctl daemon-reload
    systemctl enable stunnel4 >/dev/null 2>&1
    systemctl restart stunnel4 >/dev/null 2>&1
    
    ui_hr
    echo -e "${GREEN}✓ SSL (STUNNEL4) INSTALADO CON ÉXITO EN PUERTO: $SSLPORT${NC}"
    ui_pause
}

ssl_stunel_2() {
    ui_header "AGREGAR PUERTO SSL ADICIONAL"
    
    if [[ ! -f /etc/stunnel/stunnel.conf ]]; then
        echo -e "${RED}❌ Stunnel4 no está instalado. Instálalo primero.${NC}"
        ui_pause
        return 1
    fi
    
    echo -e "${WHITE}Seleccione el puerto de anclaje local activo...${NC}"
    while true; do
        read -p "Puerto Local (Ancla): " portx
        if [[ -n "$portx" ]]; then
            if mportas | grep -q -w "$portx"; then
                break
            else
                echo -e "${RED}❌ Puerto inválido o inactivo. Intente con uno activo.${NC}"
            fi
        fi
    done
    
    ui_hr
    echo -e "${WHITE}Seleccione el nuevo puerto SSL adicional...${NC}"
    while true; do
        read -p "Puerto SSL Adicional: " SSLPORT
        if ! mportas | grep -q -w "$SSLPORT"; then
            break
        else
            echo -e "${RED}❌ Puerto $SSLPORT ya está en uso. Elige otro.${NC}"
        fi
    done
    
    ui_hr
    echo -e "${YELLOW}[+] Agregando puerto extra a stunnel.conf...${NC}"
    cat <<EOF >>/etc/stunnel/stunnel.conf

[SSL+]
cert = /etc/stunnel/stunnel.pem
accept = ${SSLPORT}
connect = 127.0.0.1:${portx}
EOF

    ufw allow ${SSLPORT}/tcp >/dev/null 2>&1
    systemctl restart stunnel4 >/dev/null 2>&1
    
    ui_hr
    echo -e "${GREEN}✓ PUERTO SSL $SSLPORT AGREGADO CON ÉXITO${NC}"
    ui_pause
}

cert_ssl_manual() {
    ui_header "AGREGAR CERTIFICADO MANUAL (ZIP)"
    
    if [[ ! -f /etc/stunnel/stunnel.conf ]]; then
        echo -e "${RED}❌ Stunnel4 no está instalado.${NC}"
        ui_pause
        return 1
    fi
    
    echo -e "${WHITE}Sube tu certificado comprimido en ZIP a un servidor de descargas (como Dropbox/Drive)${NC}"
    echo -e "El ZIP debe contener: ${YELLOW}private.key${NC}, ${YELLOW}certificate.crt${NC} y ${YELLOW}ca_bundle.crt${NC}\n"
    
    read -p "Pegue el link de descarga directa: " linkd
    if [[ -z "$linkd" ]]; then
        echo -e "${RED}❌ Enlace vacío.${NC}"
        ui_pause
        return 1
    fi
    
    ui_hr
    echo -e "${YELLOW}[+] Descargando certificado...${NC}"
    wget -qO /etc/stunnel/certificado.zip "$linkd"
    
    if [[ ! -f /etc/stunnel/certificado.zip ]]; then
        echo -e "${RED}❌ Error al descargar el archivo ZIP.${NC}"
        ui_pause
        return 1
    fi
    
    cd /etc/stunnel/ || exit
    unzip -o certificado.zip >/dev/null 2>&1
    
    if [[ -f private.key && -f certificate.crt ]]; then
        echo -e "${YELLOW}[+] Instalando certificado...${NC}"
        if [[ -f ca_bundle.crt ]]; then
            cat private.key certificate.crt ca_bundle.crt > stunnel.pem
        else
            cat private.key certificate.crt > stunnel.pem
        fi
        rm -f private.key certificate.crt ca_bundle.crt certificado.zip
        systemctl restart stunnel4 >/dev/null 2>&1
        echo -e "${GREEN}✓ CERTIFICADO MANUAL INSTALADO CON ÉXITO${NC}"
    else
        echo -e "${RED}❌ El ZIP no contiene private.key y certificate.crt.${NC}"
        rm -f certificado.zip
    fi
    cd ~ || exit
    ui_pause
}

cert_ssl_zerossl() {
    ui_header "CERTIFICADO ZEROSSL (VALIDACIÓN HTTP)"
    
    if [[ ! -f /etc/stunnel/stunnel.conf ]]; then
        echo -e "${RED}❌ Stunnel4 no está instalado.${NC}"
        ui_pause
        return 1
    fi
    
    echo -e "${YELLOW}[+] Instalando Apache2 temporal para validación HTTP...${NC}"
    DEBIAN_FRONTEND=noninteractive apt-get install apache2 -y >/dev/null 2>&1
    
    # Mover Apache temporalmente a puerto 81 para dejar libre el 80 si lo usa otro proxy
    echo "Listen 81" >/etc/apache2/ports.conf
    service apache2 restart >/dev/null 2>&1
    
    ui_hr
    echo -e "${WHITE}Completa los datos solicitados en ZeroSSL (HTTP Validation)...${NC}"
    read -p "Nombre del Archivo de validación (ej: 530DDC.txt): " keyy
    read -p "Contenido / Datos de la llave: " dat2w
    
    mkdir -p /var/www/html/.well-known/pki-validation
    echo "$dat2w" > /var/www/html/.well-known/pki-validation/"$keyy"
    
    ui_hr
    echo -e "${YELLOW}Verifica que tu dominio responda correctamente en ZeroSSL.${NC}"
    read -p "Presiona Enter cuando hayas validado y descargado el ZIP..."
    
    ui_hr
    read -p "Pega el enlace de descarga directa del ZIP del certificado: " link
    
    if [[ -n "$link" ]]; then
        wget -qO /etc/stunnel/certificado.zip "$link"
        cd /etc/stunnel/ || exit
        unzip -o certificado.zip >/dev/null 2>&1
        if [[ -f private.key && -f certificate.crt ]]; then
            cat private.key certificate.crt ca_bundle.crt > stunnel.pem 2>/dev/null || cat private.key certificate.crt > stunnel.pem
            rm -f private.key certificate.crt ca_bundle.crt certificado.zip
            systemctl restart stunnel4 >/dev/null 2>&1
            echo -e "${GREEN}✓ CERTIFICADO ZEROSSL INSTALADO CON ÉXITO${NC}"
        else
            echo -e "${RED}❌ Error al extraer el certificado.${NC}"
        fi
        cd ~ || exit
    fi
    
    # Detener Apache temporal
    service apache2 stop >/dev/null 2>&1
    systemctl disable apache2 >/dev/null 2>&1
    ui_pause
}

gerar_cert() {
    local mode=$1 # 1: Let's Encrypt, 2: ZeroSSL
    ui_header "AUTOMATIZACIÓN ACME.SH CERTIFICADOS"
    
    echo -e "${WHITE}Requisitos: Dominio apuntado a la IP del VPS.${NC}"
    echo -e "${WHITE}Los puertos 80 y 443 deben estar temporalmente libres.${NC}\n"
    
    read -p "Ingresa tu dominio: " domain
    if [[ -z "$domain" ]]; then
        echo -e "${RED}❌ Dominio vacío.${NC}"
        ui_pause
        return 1
    fi
    
    if [[ $mode -eq 2 ]]; then
        read -p "Ingresa tu correo para ZeroSSL: " mail
        if [[ -z "$mail" ]]; then
            echo -e "${RED}❌ Correo vacío.${NC}"
            ui_pause
            return 1
        fi
    fi
    
    ui_hr
    # Liberar puerto 80 (Parar servidores web o proxies)
    echo -e "${YELLOW}[+] Liberando puertos 80 y 443...${NC}"
    service apache2 stop >/dev/null 2>&1
    service nginx stop >/dev/null 2>&1
    killall -9 PDirect.py POpen.py PPub.py PPriv.py 2>/dev/null
    
    # Instalar acme.sh si no existe
    if [[ ! -f ~/.acme.sh/acme.sh ]]; then
        echo -e "${YELLOW}[+] Instalando acme.sh...${NC}"
        curl -s https://get.acme.sh | sh >/dev/null 2>&1
        ~/.acme.sh/acme.sh --upgrade --auto-upgrade >/dev/null 2>&1
    fi
    
    ui_hr
    if [[ $mode -eq 1 ]]; then
        echo -e "${YELLOW}[+] Generando Certificado Let's Encrypt...${NC}"
        ~/.acme.sh/acme.sh --set-default-ca --server letsencrypt >/dev/null 2>&1
        ~/.acme.sh/acme.sh --issue -d "$domain" --standalone --keylength 2048
    else
        echo -e "${YELLOW}[+] Registrando cuenta y generando Certificado ZeroSSL...${NC}"
        ~/.acme.sh/acme.sh --register-account -m "$mail" --server zerossl >/dev/null 2>&1
        ~/.acme.sh/acme.sh --set-default-ca --server zerossl >/dev/null 2>&1
        ~/.acme.sh/acme.sh --issue -d "$domain" --standalone --keylength 2048
    fi
    
    if [[ -f ~/.acme.sh/"$domain"/"$domain".key ]]; then
        echo -e "${YELLOW}[+] Instalando certificado en Stunnel4...${NC}"
        cat ~/.acme.sh/"$domain"/"$domain".key ~/.acme.sh/"$domain"/fullchain.cer > /etc/stunnel/stunnel.pem
        systemctl restart stunnel4 >/dev/null 2>&1
        echo -e "${GREEN}✓ CERTIFICADO INSTALADO CON ÉXITO PARA EL DOMINIO $domain${NC}"
    else
        echo -e "${RED}❌ Error al generar el certificado con acme.sh.${NC}"
    fi
    ui_pause
}

while true; do
    ui_header "SSL / TLS (STUNNEL4) MANAGER"
    echo -e "  ${CYAN}[1]>${WHITE} INSTALAR / DESINSTALAR SSL (STUNNEL4)${NC}"
    echo -e "  ${CYAN}[2]>${WHITE} AGREGAR PUERTOS SSL EXTRA${NC}"
    echo -e "  ${CYAN}[3]>${WHITE} AGREGAR CERTIFICADO MANUAL (ZIP)${NC}"
    echo -e "  ${CYAN}[4]>${WHITE} AGREGAR CERTIFICADO ZEROSSL (VALIDACIÓN HTTP)${NC}"
    echo -e "  ${CYAN}[5]>${WHITE} AGREGAR CERTIFICADO AUTOMÁTICO (LET'S ENCRYPT)${NC}"
    echo -e "  ${CYAN}[6]>${WHITE} AGREGAR CERTIFICADO AUTOMÁTICO (ZEROSSL DIRECTO)${NC}"
    ui_hr
    echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
    ui_hr
    ui_prompt "Selecciona una opción: "
    read -r opcao
    
    case $opcao in
        1) ssl_stunel ;;
        2) ssl_stunel_2 ;;
        3) cert_ssl_manual ;;
        4) cert_ssl_zerossl ;;
        5) gerar_cert 1 ;;
        6) gerar_cert 2 ;;
        0) break ;;
        *) continue ;;
    esac
done
