#!/bin/bash
clear
echo -e "\033[1;36m=========================================================\033[0m"
echo -e "\033[1;33m          CAMBIAR CONTRASEÑA DE ROOT Y ACCESO SSH         \033[0m"
echo -e "\033[1;36m=========================================================\033[0m\n"

# Check if run as root
if [ "$EUID" -ne 0 ]; then
    echo -e "\033[1;31m❌ Acceso Denegado. Solo root puede ejecutar esto.\033[0m"
    sleep 2
    exit 1
fi

ROOT_HASH=$(grep "^root:" /etc/shadow | cut -d: -f2)

if [[ "$ROOT_HASH" == "*" ]] || [[ "$ROOT_HASH" == "!" ]] || [[ -z "$ROOT_HASH" ]]; then
    echo -e "\033[1;33m[!] Root no tiene contraseña asignada actualmente (Común en AWS/GCP).\033[0m"
    echo -e "\033[1;33m[!] Se procederá directamente a asignar una nueva contraseña.\033[0m\n"
else
    echo -e "\033[1;37mPor seguridad, ingresa la contraseña actual de root:\033[0m"
    read -s -p "Contraseña actual: " current_pass
    echo ""
    
    export CURR_PASS="$current_pass"
    if ! python3 -c '
import crypt, spwd, sys, os
pwd = os.environ.get("CURR_PASS", "")
try:
    enc_pwd = spwd.getspnam("root").sp_pwd
    if crypt.crypt(pwd, enc_pwd) == enc_pwd:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
' 2>/dev/null; then
        echo -e "\033[1;31m[!] Contraseña incorrecta. Acceso denegado.\033[0m"
        sleep 2
        exit 1
    fi
    echo -e "\033[1;32m[+] Contraseña verificada correctamente.\033[0m\n"
fi

echo -e "\033[1;37mIngresa la nueva contraseña para root:\033[0m"
read -s -p "Nueva contraseña: " new_pass1
echo ""
read -s -p "Confirma la nueva contraseña: " new_pass2
echo ""

if [[ "$new_pass1" != "$new_pass2" ]]; then
    echo -e "\033[1;31m[!] Las contraseñas no coinciden. Intenta de nuevo.\033[0m"
    sleep 2
    exit 1
fi

if [[ -z "$new_pass1" ]]; then
    echo -e "\033[1;31m[!] La contraseña no puede estar vacía.\033[0m"
    sleep 2
    exit 1
fi

echo "root:$new_pass1" | chpasswd
if [ $? -eq 0 ]; then
    echo -e "\033[1;32m[+] Contraseña de root actualizada exitosamente.\033[0m"
    
    # Habilitar login por SSH
    sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/g' /etc/ssh/sshd_config
    sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config
    
    # AWS / Cloud overriding
    if [ -d /etc/ssh/sshd_config.d ]; then
        sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config.d/*.conf 2>/dev/null
    fi
    
    systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null
    echo -e "\033[1;32m[+] Acceso SSH por contraseña para root habilitado.\033[0m"
else
    echo -e "\033[1;31m[!] Error al cambiar la contraseña.\033[0m"
fi

echo ""
read -n 1 -s -r -p "Presiona cualquier tecla para continuar..."
