#!/bin/bash
# Maximus Timezone Changer
# Adapted from Chumo's LATAM script

# Colors
RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
WHITE='\033[1;37m'
NC='\033[0m'

# UI helpers
ui_hr() { echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"; }
ui_subhr() { echo -e "${CYAN}───────────────────────────────────────────────────────${NC}"; }
ui_prompt() { echo -ne "${YELLOW}$1${NC}"; }
ui_pause() { read -p "Presiona Enter para volver..." ; }

draw_banner() {
    clear
    if [ -f "/etc/MaximusVpsMx/ascii-text-art.txt" ]; then
        cat "/etc/MaximusVpsMx/ascii-text-art.txt"
    else
        echo -e "${CYAN}   __  __             _                      "
        echo "  |  \/  |           (_)                     "
        echo "  | \  / | __ ___  ___ _ __ ___  _   _ ___   "
        echo "  | |\/| |/ _\` \ \/ / | '_ \` _ \ \| | | / __|  "
        echo "  | |  | | (_| |>  <| | | | | | | |_| \__ \  "
        echo "  |_|  |_|\__,_/_/\_\_|_| |_| |_|\__,_|___/  ${NC}"
    fi
}

ui_header() {
    draw_banner
    ui_hr
    echo -e "           ${YELLOW}AJUSTE DE HORARIO LOCAL / ZONA HORARIA${NC}"
    ui_hr
}

change_timezone() {
    local zone="$1"
    local name="$2"
    if [ -f "/usr/share/zoneinfo/$zone" ]; then
        rm -f /etc/localtime
        ln -s "/usr/share/zoneinfo/$zone" /etc/localtime
        # Actualizar /etc/timezone si existe
        if [ -f /etc/timezone ]; then
            echo "$zone" > /etc/timezone
        fi
        echo -e "\n${GREEN}[✓] Zona horaria cambiada a: $name ($zone)${NC}"
        echo -e "${YELLOW}Fecha/Hora actual: $(date)${NC}"
    else
        echo -e "\n${RED}[❌] Error: La zona horaria $zone no está disponible en este sistema.${NC}"
    fi
}

while true; do
    ui_header
    echo -ne "  ${CYAN}ZONA ACTUAL:${NC} ${WHITE}"
    if [ -f /etc/timezone ]; then
        cat /etc/timezone
    else
        readlink /etc/localtime | sed 's#.*/zoneinfo/##'
    fi
    echo -e "${NC}"
    echo -e "  ${CYAN}FECHA/HORA :${NC} ${GREEN}$(date)${NC}"
    ui_subhr
    echo -e "  ${CYAN}[1]>${WHITE} Cambiar a Hora Local México (Merida)${NC}"
    echo -e "  ${CYAN}[2]>${WHITE} Cambiar a Hora Local Argentina (Buenos Aires)${NC}"
    echo -e "  ${CYAN}[3]>${WHITE} Cambiar a Hora Local Colombia (Bogota)${NC}"
    echo -e "  ${CYAN}[4]>${WHITE} Cambiar a Hora Local Perú (Lima)${NC}"
    echo -e "  ${CYAN}[5]>${WHITE} Cambiar a Hora Local Guatemala${NC}"
    echo -e "  ${CYAN}[6]>${WHITE} Cambiar a otra Zona Horaria (Ingreso Manual)${NC}"
    ui_hr
    echo -e "  ${WHITE}[0] VOLVER AL MENÚ ANTERIOR${NC}"
    ui_hr
    ui_prompt " Selecciona una opción: "
    read opt
    
    case $opt in
        1) change_timezone "America/Merida" "México" ; ui_pause ;;
        2) change_timezone "America/Argentina/Buenos_Aires" "Argentina" ; ui_pause ;;
        3) change_timezone "America/Bogota" "Colombia" ; ui_pause ;;
        4) change_timezone "America/Lima" "Perú" ; ui_pause ;;
        5) change_timezone "America/Guatemala" "Guatemala" ; ui_pause ;;
        6) 
            echo -e "\n${YELLOW}Ejemplos: America/Mexico_City, America/Caracas, Europe/Madrid, etc.${NC}"
            ui_prompt " Ingresa la zona horaria: "
            read custom_zone
            if [ ! -z "$custom_zone" ]; then
                change_timezone "$custom_zone" "Personalizada"
            else
                echo -e "${RED}Entrada vacía.${NC}"
            fi
            ui_pause
            ;;
        0) exit 0 ;;
        *) continue ;;
    esac
done
