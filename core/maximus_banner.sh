#!/bin/bash
# Maximus Dynamic PAM Banner

# El módulo pam_exec exporta la variable PAM_USER con el nombre del usuario
username="$PAM_USER"

# Si no hay usuario, salir silenciosamente
[ -z "$username" ] && exit 0

# Excepción para el root y usuarios administradores (sudoers)
if [ "$username" == "root" ] || id -nG "$username" 2>/dev/null | grep -qw "sudo"; then
    display_user="$username (Admin)"
else
    db_line=$(grep "^${username}:" /etc/MaximusVpsMx/users.db 2>/dev/null)
    
    # SI NO ESTÁ EN LA DB, ES UN USUARIO FANTASMA (Orphan) -> DESCONECTAR INMEDIATAMENTE
    if [ -z "$db_line" ]; then
        echo -e "\n\n❌ ERROR: Cuenta no registrada o eliminada de la Base de Datos."
        echo -e "Por favor, contacte a su administrador."
        # Matar el proceso padre (SSH) para desconectar al intruso
        kill -9 $PPID 2>/dev/null
        exit 0
    fi
    
    exp_date=$(echo "$db_line" | cut -d: -f3 2>/dev/null)
    pass_type=$(echo "$db_line" | cut -d: -f2 2>/dev/null)
    alias_name=$(echo "$db_line" | cut -d: -f6 2>/dev/null)
    
    if [ "$pass_type" == "HWID_INV" ] && [ -n "$alias_name" ]; then
        display_user="$alias_name"
    else
        display_user="$username"
    fi
fi

# El banner visual ahora se sirve desde /etc/dropbear/banner (pre-auth)
# Aquí solo enviamos los datos de la cuenta del usuario (ligero, sin HTML)

echo -e "⚡ DETALLES DE SU SERVIDOR ⚡"
echo ""
echo -e "🛡️ USUARIO : $display_user"

if [ -n "$exp_date" ]; then
    today=$(date +%s)
    exp=$(date -d "$exp_date" +%s)
    days_left=$(( (exp - today) / 86400 ))
    
    # Formatear la fecha a 'May 02, 2026'
    formatted_date=$(date -d "$exp_date" "+%b %d, %Y")
    
    echo -e "📅 VALIDO  : $formatted_date"
    echo -e "⏳ RESTAN  : $days_left DIAS"
else
    echo -e "📅 VALIDO  : Ilimitado"
    echo -e "⏳ RESTAN  : Ilimitados"
fi

echo ""

# Finalizar inmediatamente para no retrasar la conexión SSH
exit 0
