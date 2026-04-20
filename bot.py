import telebot
from telebot import types
import core.manager as manager
import core.database as db
import config
import os
import time

# Inicialización segura de Bot y DB
if config.BOT_TOKEN == "PENDIENTE" or not config.BOT_TOKEN:
    print("❌ ERROR: No se ha configurado el TOKEN del Bot. Usa el menú MX para configurarlo.")
    exit(1)

try:
    bot = telebot.TeleBot(config.BOT_TOKEN)
    db.init_db()
except Exception as e:
    print(f"❌ ERROR CRÍTICO al inicializar: {e}")
    exit(1)

# --- HANDLERS PRINCIPALES ---

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    item_free = types.InlineKeyboardButton("🎁 Cuenta Gratis (3d)", callback_data="get_free")
    item_premium = types.InlineKeyboardButton("💎 Cuenta Premium", callback_data="get_premium")
    item_stats = types.InlineKeyboardButton("📈 Estado Servidor", callback_data="get_stats")
    item_support = types.InlineKeyboardButton("🆘 Soporte", url="https://t.me/TuSoporte")
    
    markup.add(item_free, item_premium)
    markup.add(item_stats, item_support)
    
    bot.send_message(
        message.chat.id, 
        config.WELCOME_MSG, 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "get_free":
        handle_free_trial(call.message)
    elif call.data == "get_premium":
        bot.send_message(call.message.chat.id, "✨ Iniciando solicitud Premium...")
        ask_premium_username(call.message)
    elif call.data == "get_stats":
        show_server_stats(call.message)
    elif call.data.startswith("approve_"):
        # Formato: approve_user_id_username_password
        _, client_id, username, password = call.data.split("_")
        process_admin_approval(call, client_id, username, password)

def process_admin_approval(call, client_id, username, password):
    bot.edit_message_text("⏳ Procesando creación...", call.message.chat.id, call.message.message_id)
    
    success, result = manager.create_ssh_user(username, password, days=30)
    
    if success:
        bot.edit_message_text(f"✅ Usuario `{username}` creado y entregado.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        bot.send_message(client_id, "💎 *¡TU CUENTA PREMIUM HA SIDO APROBADA!*", parse_mode="Markdown")
        deliver_account(client_id, username, password, result)
    else:
        bot.edit_message_text(f"❌ Error al crear: {result}", call.message.chat.id, call.message.message_id)

# --- FLUJO CUENTA GRATIS (TRIAL) ---

def handle_free_trial(message):
    user_id = message.chat.id
    can_get, wait_days = db.can_get_trial(user_id)
    
    if not can_get:
        bot.send_message(
            user_id, 
            f"❌ *Acceso Denegado*\nYa generaste una cuenta recientemente. Debes esperar *{wait_days} días* para otra cuenta gratuita.\n\n🚀 ¡Prueba nuestro plan Premium!", 
            parse_mode="Markdown"
        )
        return

    bot.send_message(user_id, "⏳ Generando tu cuenta de prueba de 3 días...")
    
    username = manager.generate_random_user()
    password = manager.generate_random_pass()
    
    # Crear usuario y guardar vinculación (v6.1)
    success, expiry = manager.create_ssh_user(username, password, days=3)
    if success:
        db.update_trial(user_id, message.from_user.username, username)
        deliver_account(message.chat.id, username, password, expiry)
    else:
        bot.reply_to(message, "❌ Hubo un problema al crear tu cuenta. Intenta más tarde.")

# --- FLUJO CUENTA PREMIUM ---

def ask_premium_username(message):
    msg = bot.send_message(message.chat.id, "👤 *Escribe el Nombre de Usuario que deseas:*", parse_mode="Markdown")
    bot.register_next_step_handler(msg, validate_premium_username)

def validate_premium_username(message):
    username = message.text.strip().lower()
    
    if len(username) < 4:
        msg = bot.send_message(message.chat.id, "⚠️ El usuario debe tener al menos 4 caracteres. Intenta de nuevo:")
        bot.register_next_step_handler(msg, validate_premium_username)
        return

    if manager.check_user_exists(username):
        msg = bot.send_message(message.chat.id, "🚫 *Este usuario ya está en uso.* Por favor, elige otro:")
        bot.register_next_step_handler(msg, validate_premium_username)
        return

    ask_premium_password(message, username)

def ask_premium_password(message, username):
    msg = bot.send_message(message.chat.id, f"🔑 Perfecto, ahora elige una contraseña para el usuario *{username}*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_premium_creation, username)

def process_premium_creation(message, username):
    password = message.text.strip()
    user_id = message.chat.id
    
    # Lógica de Validación de Pago (Simulación de Envío al Admin)
    bot.send_message(user_id, "📡 *Enviando solicitud de aprobación al Administrador...*", parse_mode="Markdown")
    
    # Notificar al Admin
    if config.ADMIN_ID != 0:
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("✅ APROBAR Y CREAR", callback_data=f"approve_{user_id}_{username}_{password}")
        markup.add(btn)
        bot.send_message(config.ADMIN_ID, f"🔔 *NUEVA SOLICITUD PREMIUM*\nUsuario: `{username}`\nRemitente: @{message.from_user.username}", reply_markup=markup, parse_mode="Markdown")

# --- ENTREGA DE DATOS ---

def deliver_account(chat_id, user, pw, expiry):
    ip = config.HOST_DOMAIN if config.HOST_DOMAIN else manager.get_server_ip()
    
    # Formatos HTTP Custom
    hc_ssl = f"{ip}:443@{user}:{pw}"
    hc_dir = f"{ip}:80@{user}:{pw}"
    
    # Formato UDP Custom corregido
    udp_link = f"{ip}:{config.UDP_RANGE}@{user}:{pw}"
    
    # Enlace Hysteria v2 dinámico
    hy_port = manager.get_hysteria_port()
    hy_obfs = manager.get_hysteria_obfs()
    hy_link = f"hy2://{pw}@{ip}:{hy_port}?insecure=1&sni={config.HY_SNI}&obfs=salamander&obfs-password={hy_obfs}#{user}"
    
    msg = f"""
🌐 *TU CUENTA SE GENERÓ CON ÉXITO* 🛡️

👤 Usuario: `{user}`
🔑 Contraseña: `{pw}`
📅 Expiración: `{expiry}`
IP Servidor: `{ip}`

🚀 *CONFIGURACIÓN HTTP CUSTOM*
• SSL: `{hc_ssl}`
• DIRECTO: `{hc_dir}`

📡 *UDP CUSTOM*
`{udp_link}`

🌀 *ENLACE HYSTERIA v2*
`{hy_link}`
Rango: `{config.HYSTERIA_RANGE}`

_Toca los códigos para copiarlos directamente._
"""
    bot.send_message(chat_id, msg, parse_mode="Markdown")

# --- SISTEMA TELÉMETRICO ---

@bot.callback_query_handler(func=lambda call: call.data == "show_stats")
def handle_stats_query(call):
    show_server_stats(call.message.chat.id, call.message.from_user.id)

def show_server_stats(chat_id, user_id=None):
    # Telemetría Global
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    msg = f"""
📊 *ESTADO DEL SERVIDOR* 🛡️
━━━━━━━━━━━━━━━━━━
🔹 *CPU:* `{cpu}%`
🔹 *RAM:* `{mem}%`
🔹 *Disco:* `{disk}%`
━━━━━━━━━━━━━━━━━━
"""
    # Telemetría Personal (v6.1)
    kb = types.InlineKeyboardMarkup()
    if user_id:
        u_info = db.get_user_status(user_id)
        if u_info and u_info.get("system_user"):
            s_user = u_info["system_user"]
            msg += f"👤 *TU CUENTA:* `{s_user}`\n"
            msg += "✨ *ESTADO:* `ACTIVA` ✅\n"
            msg += "━━━━━━━━━━━━━━━━━━\n"
            kb.add(types.InlineKeyboardButton("🔄 RENOVAR (VER 5 ADS)", callback_data=f"renew_ads_{s_user}"))
    
    kb.add(types.InlineKeyboardButton("⬅️ Volver", callback_data="start"))
    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("renew_ads_"))
def process_renew_ads(call):
    s_user = call.data.replace("renew_ads_", "")
    
    # Secuencia de 5 anuncios (Simulada)
    for i in range(1, 6):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🎬 *VIENDO ANUNCIO {i}/5...*\n\n_Por favor no cierres este mensaje para recibir tu recompensa._",
            parse_mode="Markdown"
        )
        time.sleep(5)
    
    # Aplicar renovación real
    new_exp = manager.extend_user_expiry(s_user, days=1)
    
    final_msg = f"""
✅ *¡RENOVACIÓN EXITOSA!* 🚀✨
━━━━━━━━━━━━━━━━━━━━
Tu cuenta `{s_user}` ha sido extendida 24 horas más.

📅 *Nueva Expiración:* `{new_exp}`
━━━━━━━━━━━━━━━━━━━━
¡Gracias por apoyar el servidor viendo anuncios!
"""
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📊 Ver Estado", callback_data="show_stats"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=final_msg,
        parse_mode="Markdown",
        reply_markup=kb
    )

if __name__ == "__main__":
    try:
        print("🚀 Bot Maximus Premium en ejecución...")
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ El Bot ha colapsado: {e}")
        time.sleep(10)
