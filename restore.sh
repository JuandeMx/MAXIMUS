#!/bin/bash
# Script de Restauración de Usuarios MAXIMUS
# Este script recupera todos los usuarios borrados por error con sus fechas exactas.

echo "=========================================="
echo " INICIANDO RESTAURACIÓN DE USUARIOS"
echo "=========================================="

# Limpiar las bases de datos para evitar duplicados si quedaban restos
> /etc/MaximusVpsMx/users.db
> /etc/MaximusVpsMx/hysteria_users.db

restore_user() {
    local user=$1
    local pass=$2
    local exp=$3
    local hwid=$4
    local limit=$5

    echo "Restaurando usuario: $user"

    # Intentar crear el usuario en Linux
    useradd -M -s /bin/false -e "$exp" "$user" 2>/dev/null
    
    # Si el usuario ya existía en Linux, solo actualizar su fecha de expiración
    if [ $? -ne 0 ]; then
        chage -E "$exp" "$user" 2>/dev/null
    fi

    # Establecer la contraseña
    echo "$user:$pass" | chpasswd

    # Guardar en base de datos de MX
    echo "$user:$pass:$exp:$hwid:$limit" >> /etc/MaximusVpsMx/users.db

    # Guardar en base de datos de Hysteria
    echo "$user:$pass:$exp:100:100" >> /etc/MaximusVpsMx/hysteria_users.db
}

# Lista de usuarios a restaurar
restore_user "Juande" "mx" "2026-05-01" "OFF" "1"
restore_user "Hugo" "123" "2026-05-24" "OFF" "1"
restore_user "Juan" "123" "2026-05-24" "OFF" "1"
restore_user "Andrea" "1234" "2026-05-25" "OFF" "1"
restore_user "Oscar" "Paciencia" "2026-05-25" "OFF" "1"
restore_user "Facu" "Walter" "2026-05-25" "OFF" "1"
restore_user "Mario" "Cliente" "2026-05-26" "OFF" "1"
restore_user "myreyna" "bella" "2026-05-26" "OFF" "1"
restore_user "Ariel" "Byjuande" "2026-05-27" "OFF" "1"
restore_user "prueba" "p1" "2026-04-28" "OFF" "100"
restore_user "Prueba1" "Pruebacliente" "2026-05-05" "OFF" "1"
restore_user "Clientemartes" "Martes" "2026-05-28" "OFF" "1"
restore_user "Rooh" "Rooh1" "2026-05-28" "OFF" "1"
restore_user "Sergio" "Cliente1" "2026-05-28" "OFF" "1"
restore_user "Cliente-hija" "Hija10" "2026-05-28" "OFF" "1"
restore_user "Pepito" "Buchaina" "2026-05-05" "OFF" "1"
restore_user "Alberto" "Alberto1" "2026-05-29" "OFF" "1"
restore_user "Juaquin" "Juaquin1" "2026-05-29" "OFF" "1"
restore_user "Juaquin2" "Juaquin2" "2026-05-29" "OFF" "1"
restore_user "Marcelo" "Marcelo" "2026-05-29" "OFF" "1"
restore_user "Santiago" "Santiago" "2026-05-29" "OFF" "1"
restore_user "Tiziano" "Tiziano" "2026-05-29" "OFF" "1"
restore_user "Armando" "Armando" "2026-05-29" "OFF" "1"
restore_user "Marcela" "Marcela" "2026-05-29" "OFF" "1"
restore_user "Lauturo" "Lautaru" "2026-05-29" "OFF" "1"
restore_user "Alfredo" "Alfredo" "2026-05-29" "OFF" "1"
restore_user "Gogy2" "Gogy2" "2026-05-29" "OFF" "1"
restore_user "Pedro" "Pedrogay" "2026-05-30" "OFF" "1"
restore_user "Rodrigo" "ElAmerica" "2026-05-30" "OFF" "1"
restore_user "Noconecta" "Tuhermana" "2026-05-30" "OFF" "1"
restore_user "Luciana" "Arg" "2026-05-30" "OFF" "1"
restore_user "Federico" "Cliente100" "2026-05-30" "OFF" "1"
restore_user "Alex" "Alexcito" "2026-05-30" "OFF" "1"
restore_user "Jhona" "Tortilla" "2026-05-30" "OFF" "1"

echo "=========================================="
echo " ✅ RESTAURACIÓN COMPLETADA CON ÉXITO"
echo "=========================================="
