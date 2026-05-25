#!/bin/bash
# Compilador y Empaquetador de MAXIMUS (Anti-Robo)

echo -e "\e[1;36m=========================================\e[0m"
echo -e "\e[1;36m   [+] INICIANDO COMPILACIÓN DE MAXIMUS  \e[0m"
echo -e "\e[1;36m=========================================\e[0m"

# 1. Instalar dependencias si no existen
if ! command -v shc &> /dev/null; then
    echo -e "\e[1;33m[!] Instalando SHC (Shell Script Compiler)...\e[0m"
    apt-get update -y
    apt-get install shc -y
fi

if ! command -v makeself &> /dev/null; then
    echo -e "\e[1;33m[!] Instalando Makeself...\e[0m"
    apt-get install makeself -y
fi

# 2. Preparar directorio temporal
WORK_DIR="/tmp/maximus_build"
rm -rf $WORK_DIR 2>/dev/null
mkdir -p $WORK_DIR

# 3. Copiar archivos originales
cp -r /etc/MaximusVpsMx/* $WORK_DIR/
# Eliminar bases de datos locales y archivos sensibles para que no vayan en el paquete
rm -f $WORK_DIR/keys.db
rm -f $WORK_DIR/cloudflare.conf
rm -f $WORK_DIR/domain.conf
rm -f $WORK_DIR/.master_node
rm -f $WORK_DIR/license.key
# Borrar el servidor Python ya que los clientes no lo necesitan
rm -f $WORK_DIR/core/key_server.py

# 4. Compilación Binaria con SHC
echo -e "\e[1;32m[+] Ofuscando código fuente a binarios...\e[0m"
cd $WORK_DIR

# Compilar MX (el menú principal)
shc -f MX
mv MX.x MX
rm MX.x.c MX.x.sh MX.c 2>/dev/null

# Compilar core scripts (opcional, los más críticos)
if [ -f "core/speed_optimize.sh" ]; then
    shc -f core/speed_optimize.sh
    mv core/speed_optimize.sh.x core/speed_optimize.sh
    rm core/speed_optimize.sh.x.c core/speed_optimize.sh.c 2>/dev/null
fi

# 5. Crear el script instalador interno (setup.sh) que moverá los archivos
cat << 'EOF' > setup.sh
#!/bin/bash
# Este script se ejecuta en RAM después de que makeself extrae el paquete
echo -e "\e[1;32m[+] Instalando archivos binarios del sistema...\e[0m"
mkdir -p /etc/MaximusVpsMx
cp -r * /etc/MaximusVpsMx/
rm -f /etc/MaximusVpsMx/setup.sh

# Preparar enlaces directos
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/MX
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/menu
ln -sf /etc/MaximusVpsMx/MX /usr/local/bin/MENU
chmod 700 /etc/MaximusVpsMx/MX
chmod +x /etc/MaximusVpsMx/core/*.sh 2>/dev/null

echo -e "\e[1;32m[+] Instalación Binaria Exitosa.\e[0m"
EOF
chmod +x setup.sh

# 6. Empaquetar con makeself
echo -e "\e[1;32m[+] Empaquetando en instalador blindado (.run)...\e[0m"
cd /tmp
makeself --quiet $WORK_DIR maximus_client.run "MaximusVpsMx Core" ./setup.sh

# 7. Despliegue
mv maximus_client.run /etc/MaximusVpsMx/maximus_client.run
rm -rf $WORK_DIR

echo -e "\e[1;36m=========================================\e[0m"
echo -e "\e[1;32m   [+] COMPILACIÓN EXITOSA               \e[0m"
echo -e "\e[1;36m=========================================\e[0m"
echo -e "El paquete instalador está listo en: /etc/MaximusVpsMx/maximus_client.run"
