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

restore_hwid() {
    local alias=$1
    local hwid=$2
    local exp=$3

    # Convertir el HWID a minúsculas
    local linux_user=$(echo "$hwid" | tr '[:upper:]' '[:lower:]')
    local password="$linux_user"
    local limit=1

    echo "Restaurando HWID: $alias ($hwid)"

    # Intentar crear el usuario en Linux
    useradd -M -s /bin/false -e "$exp" "$linux_user" 2>/dev/null
    
    # Si el usuario ya existía en Linux, solo actualizar su fecha de expiración
    if [ $? -ne 0 ]; then
        chage -E "$exp" "$linux_user" 2>/dev/null
    fi

    # Establecer la contraseña
    echo "$linux_user:$password" | chpasswd

    # Guardar en base de datos de MX (formato HWID: user:HWID_INV:exp:HWID:limit:alias)
    echo "$linux_user:HWID_INV:$exp:$hwid:$limit:$alias" >> /etc/MaximusVpsMx/users.db

    # Guardar en base de datos de Hysteria
    echo "$linux_user:$password:$exp:100:100" >> /etc/MaximusVpsMx/hysteria_users.db
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
restore_hwid "Juande" "39944e07eaeca54252e573bb57e1cc89" "2027-03-18"
restore_hwid "alexis" "8" "2026-06-24"
restore_hwid "maria" "d73671d605682c238a6edce84b3760bb" "2026-06-24"
restore_hwid "marcos" "e2512b1e498e42a0e550ba8ddee5e997" "2026-06-27"
restore_hwid "señora de juan" "6653679ed74c3863bc08d42b7c1eabf9" "2026-06-29"
restore_hwid "novia juan" "b5bd88df86389aacd2a151cf6310f96c" "2026-06-29"
restore_hwid "renovacion z1" "d4f6cd1511563cc3f31a2081a94af2d1" "2026-06-29"
restore_hwid "Magui" "838c2ac248af31f9ed029a37373a16cc" "2026-06-30"
restore_hwid "mailin" "84108ee2b1461f0988d733d6c5a09d3b" "2026-06-30"
restore_hwid "gabriel" "5c5ff63128018315c4391ea19f5392bf" "2026-06-30"
restore_hwid "Juande2" "aa53afb6aa4924508711cf2bee2ab64f" "2026-06-30"
restore_hwid "albertoo" "308ed2f5427bf286ca5c5ed041b4b3f0" "2026-07-01"
restore_hwid "diego1" "2cb14782126b76ac5b94409952323ebe" "2026-07-01"
restore_hwid "martita" "d691847043d57d7f2881ebf54f748668" "2026-07-01"
restore_hwid "clienta21" "c5faba118028adf2b47e4044f29e79fb" "2026-06-25"
restore_hwid "mabel" "5cf11600a30c8bee4435d951de3126eb" "2026-07-03"
restore_hwid "Sergio" "5e6f9215df0b888829422a7dcb7de06e" "2026-07-03"
restore_hwid "cliente nuevo" "32cb729f64333e35309c89af746f46c3" "2026-07-04"
restore_hwid "pigin" "098b451d350e9ce383bd4fa8228545fd" "2026-07-04"
restore_hwid "kino" "b94084bb6829fed8738240a742c4777d" "2026-07-04"
restore_hwid "argentina" "bf08799c5f4a0e14fbe7c3329f947dc2" "2026-07-05"
restore_hwid "simon" "d8f1ab984e350fee0724f82ce31458e7" "2026-07-05"
restore_hwid "graciela" "7f86a4b056bee48f4a2a68390c4ae90a" "2026-07-06"
restore_hwid "maia" "e0104dfa207b674318a90c7cdda6b1fe" "2026-07-06"
restore_hwid "clate" "333465281f369fa760320cd0b2443c06" "2026-07-07"
restore_hwid "vibrr" "7de1bdd55d47e8d29b1531f9fc857540" "2026-07-08"
restore_hwid "ivna02" "0ee1c2cfb24f8426e319061642b174ea" "2026-07-08"
restore_hwid "kdje" "2545e2f6a1ac38b0eb4e34dcd17057ad" "2026-07-08"
restore_hwid "gay10" "4645d3545a0069880f97e917ab8ecefe" "2026-07-08"
restore_hwid "Tiziqnorenovar" "975b59403196ae78fd9823276449969f" "2026-07-08"
restore_hwid "Tiziano" "d0a7994794d63d5a4cf5d3d1758bb2c7" "2026-07-08"
restore_hwid "cliente amigo" "929a4abc25a660b661fbdc02baf55b78" "2026-07-09"
restore_hwid "Johana" "93f149e880d27733ca4315e07b2f42c9" "2026-07-10"
restore_hwid "cli" "0553148cdf2b05ce0c81da0187160e1b" "2026-07-02"
restore_hwid "señora" "2e397189ffa81fec262465972297e0e4" "2026-07-09"
restore_hwid "si o no" "296d0821211dc379475df8e7ef546767" "2026-07-09"
restore_hwid "jose30" "eb10d916775131dbc8f118a2bce4f1b0" "2026-07-09"
restore_hwid "borro" "14a354a3341013ca9449afba1641a02c" "2026-06-25"
restore_hwid "cliente" "ee4ed9fbb507619e3ab2dd72de14ce01" "2026-07-10"
restore_hwid "martin" "53e89a225ada0c9708e9037ffe06a748" "2026-07-10"
restore_hwid "Gisela" "1145790bf3b3b2b7d4de36600de0c3f8" "2026-07-10"
restore_hwid "keke" "6ce261533b460bbcdcd671a2427b1025" "2026-07-05"
restore_hwid "limon" "b270c7c6a352268921ac1ef862492271" "2026-07-10"
restore_hwid "cliente5" "0deb43efcdc893c6a264e3c082377561" "2026-07-11"
restore_hwid "cliente 01" "8951b1fd5428f4ed5b79b83c17c3e6c6" "2026-07-12"
restore_hwid "cliente10" "757b8b440287b3fbf32b4cb2a00d1db5" "2026-07-14"
restore_hwid "cliente01" "f32fda3169b122ad6d47023dd77add3b" "2026-07-14"
restore_hwid "hiy" "80726ffc849643c2caf482016ccb88a9" "2026-06-30"
restore_hwid "cliente" "2528f96b63b09a5b3d91a35f7ec2cb3c" "2026-07-12"
restore_hwid "cli3" "dc51ffebe28234087408167ec7b8d710" "2026-07-15"
restore_hwid "cliente" "c8b8275f3e24d0d86526c5f3d9a4cfad" "2026-07-15"
restore_hwid "cliente10" "f347f7f778d7ff59b8505a944e3a8beb" "2026-07-15"
restore_hwid "reclamo" "e24e2387185bf668bb76298e20577964" "2026-07-15"
restore_hwid "lisandro" "5720695dae4be1fa1a74646cbe1871da" "2026-06-25"
restore_hwid "Graciela" "e3a275c563b7a8c52477e2343f575bb6" "2026-07-12"
restore_hwid "joselita" "f4ec57fe915f7f590bb8b10f752f1b1f" "2026-07-14"
restore_hwid "clienta" "a2e6f494f07751cd7156f9af0d21a813" "2026-07-07"
restore_hwid "Yomero" "2c38800e97cc5887b1b3df2e89b20bb0" "2027-07-28"

echo "=========================================="
echo " ✅ RESTAURACIÓN COMPLETADA CON ÉXITO"
echo "=========================================="
