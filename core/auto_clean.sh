#!/bin/bash
# Maximus Elite - Sistema de Auto-Limpieza
# Ejecutado vía Cron diariamente para evitar problemas de almacenamiento

# Asegurar privilegios root
if [ "$EUID" -ne 0 ]; then
    echo "Este script debe ser ejecutado como root."
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando limpieza profunda del sistema..." >> /var/log/MaximusVpsMx/auto_clean.log

# 1. Purgar logs antiguos de systemd/journald
echo "Limpiando logs del sistema (journald)..."
journalctl --vacuum-time=1d >/dev/null 2>&1
journalctl --vacuum-size=10M >/dev/null 2>&1

# 1.5 Vaciado de Logs Activos Gigantes (Evita que syslog llegue a 80GB)
echo "Vaciando logs activos pesados..."
find /var/log -type f -name "*.log" -exec truncate -s 0 {} \; 2>/dev/null
truncate -s 0 /var/log/syslog /var/log/messages /var/log/auth.log /var/log/kern.log /var/log/daemon.log /var/log/debug 2>/dev/null
rm -rf /var/log/journal/*/*.journal~ 2>/dev/null

# 2. Limpiar cache de APT (instalaciones)
echo "Limpiando cache de APT y paquetes huérfanos..."
apt-get autoremove -y >/dev/null 2>&1
apt-get clean >/dev/null 2>&1

# 3. Eliminar logs rotados antiguos
echo "Limpiando logs rotados en /var/log..."
rm -f /var/log/*.gz /var/log/*.[0-9] 2>/dev/null
rm -f /var/log/**/*.gz /var/log/**/*.[0-9] 2>/dev/null

# 4. Limpiar archivos temporales
echo "Limpiando archivos temporales..."
find /tmp -type f -atime +2 -delete 2>/dev/null
find /var/tmp -type f -atime +2 -delete 2>/dev/null

# 5. Limpiar cachés de memoria RAM
echo "Liberando cachés de memoria RAM..."
sync; echo 3 > /proc/sys/vm/drop_caches

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Limpieza finalizada." >> /var/log/MaximusVpsMx/auto_clean.log
exit 0
