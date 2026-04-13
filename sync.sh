#!/bin/bash
# MaximusVpsMx - GitHub Synchronizer
# Automatiza el respaldo de cambios del panel al repositorio oficial.

CYAN='\033[1;36m'
GREEN='\033[1;32m'
NC='\033[0m'

echo -e "${CYAN}=======================================================${NC}"
echo -e "${CYAN}         GITHUB AUTO-SYNC: MAXIMUS VPS MX${NC}"
echo -e "${CYAN}=======================================================${NC}"

# Verificar si estamos en un repositorio git
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo -e "❌ Error: Este directorio no es un repositorio de Git."
    exit 1
fi

FECHA_SYNC=$(date +"%Y-%m-%d %H:%M:%S")

echo -e "[+] Preparando cambios..."
git add .

echo -e "[+] Realizando Commit (Auto-update: $FECHA_SYNC)..."
git commit -m "Auto-update MaximusVpsMx: $FECHA_SYNC - AXOLOT SUPREMACY Edition"

echo -e "[+] Empujando cambios a GitHub (Rama: main)..."
if git push origin main; then
    echo -e "\n${GREEN}✅ Sincronización completada con éxito.${NC}"
else
    echo -e "\n${CYAN}⚠️  Hubo un problema al subir los cambios a GitHub.${NC}"
fi
echo -e "${CYAN}=======================================================${NC}"
