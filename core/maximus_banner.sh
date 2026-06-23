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

# Banner HTML completo - se muestra siempre como Server Message en HTTP Custom
cat << 'EOF'
<div style="text-align: center; font-family: 'Courier New', Courier, monospace; background-color: #0b001a; color: #d8b4fe; padding: 10px; line-height: 1.15;">
<font size="5" style="font-weight: bold; text-shadow: 0 0 8px #ffaa00;"><font color="#ffaa00">🏴‍☠️ 𝕃</font><font color="#ffffff">𝕖</font><font color="#ffaa00">𝕘</font><font color="#ffffff">𝕚</font><font color="#ffaa00">ó</font><font color="#ffffff">𝕟</font> <font color="#ff0055">𝔸ℕ𝕆ℕ𝕐𝕄𝕌𝕊</font> 🛠️</font><br>
<span style="color: #ff0055; background-color: #1a0033; padding: 1px 5px; font-weight: bold; border: 1px solid #ffaa00; font-size: 0.85em; text-shadow: 0 0 5px #ff0055;">🥷 [ AMATERAZU & TEAM ELYSA YAYLOR ] 🥷</span><br>
<font size="3" color="#ffaa00" style="text-shadow: 0 0 4px #ffaa00; font-weight: bold;">(⪧ • ⩊ • ⪦)∫</font><br>
<font size="3" color="#ff0055" style="text-shadow: 0 0 6px #ff0055;">🔥 ─── ⚡ 𝔅ℑ𝔈𝔑𝔙𝔈𝔑ℑ𝔇𝔒𝔖 ⚡ ─── 🔥</font><br>
<font size="2"><span style="color: #ffaa00; font-weight: bold; text-shadow: 0 0 3px #ffaa00;">♛ ANONYMUS ♛</span> • <span style="color: #00ffff; text-shadow: 0 0 3px #00ffff;">♜ 𝘀𝘀𝗵_𝘀𝗲𝗿𝘃𝗲𝗿𝘀 ♜</span> • <span style="color: #9d4edd;">♞ 𝗢𝗡𝗟𝗜𝗡𝗘_𝗚𝗔𝗠𝗘𝗦 ♞</span> • <span style="color: #00ff00; text-shadow: 0 0 3px #00ff00;">♟ 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 ♟</span></font><br><br>
<span style="color: #0b001a; background-color: #ffaa00; padding: 5px 10px; font-weight: bold; font-size: 1em; box-shadow: 0 0 10px #ffaa00; border-radius: 3px;">♗ [ 𝙋𝘼𝙍𝘼 𝙏𝙊𝘿𝙊𝙎 𝙎𝙄𝙉 𝘾𝙊𝙎𝙏𝙊 ] ♗</span><br><br>

<font size="3" color="#00ff00" style="font-weight: bold; text-shadow: 0 0 6px #00ff00;">🤝 ⚡ ALIANZA OFICIAL ⚡ 🤝</font><br>
<font size="2" color="#ffffff" style="font-weight: bold;">Legión ANONYMUS & FreeLatam</font><br><br>

<font size="2" color="#ffaa00" style="text-shadow: 0 0 3px #ffaa00;">▼ LEGIÓN ANONYMUS ▼</font><br>
<a href="https://chat.whatsapp.com/L05wZezLROk2QIqubI0OXg" style="color: #ffaa00; font-weight: bold; text-decoration: none; text-shadow: 0 0 4px #ffaa00; font-size: 0.85em;">https://chat.whatsapp.com/L05wZezLROk2QIqubI0OXg</a><br><br>

<font size="2" color="#00ffff" style="text-shadow: 0 0 3px #00ffff;">▼ GRUPO OFICIAL FREELATAM ▼</font><br>
<a href="https://chat.whatsapp.com/HLv74cLJzaiEDBieLIBllc" style="color: #00ff00; font-weight: bold; text-decoration: none; text-shadow: 0 0 4px #00ff00; font-size: 0.85em;">https://chat.whatsapp.com/HLv74cLJzaiEDBieLIBllc</a><br><br>

<font size="3" color="#ff0055" style="font-weight: bold; text-shadow: 0 0 6px #ff0055;">♖ MAXIMUS VPS ♖</font><br>
<font size="2" color="#ffffff"><i>"¡SI TE VENDIERON ESTE SERVIDOR ERES UN PENDEJO!"</i></font><br>
<font size="2" color="#ffaa00" style="font-weight: bold; text-shadow: 0 0 4px #ffaa00;">⚡ [JUANDE_MX] ⚡</font>
</div>
EOF

echo ""
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
