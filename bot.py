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
    
    user = manager.generate_random_user()
    pw = manager.generate_random_pass()
    
    success, result = manager.create_ssh_user(user, pw, days=3)
    
    if success:
        db.update_trial(user_id, message.from_user.username)
        deliver_account(user_id, user, pw, result)
    else:
        bot.send_message(user_id, f"❌ Error del sistema: {result}")

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
    
    # En un entorno real, aquí se esperaría el callback de aprobación.
    # Para este desarrollo inicial, creamos la estructura base.

# --- ENTREGA DE DATOS ---

def deliver_account(chat_id, user, pw, expiry):
    ip = config.HOST_DOMAIN if config.HOST_DOMAIN else manager.get_server_ip()
    
    # Formatos HTTP Custom
    hc_ssl = f"{ip}:443@{user}:{pw}"
    hc_dir = f"{ip}:80@{user}:{pw}"
    
    # Formato UDP Custom
    udp_link = f"{user}@{ip}:{config.UDP_SERVER_PORT}:{pw}"
    
    # Enlace Hysteria v2
    hy_link = f"hy2://{pw}@{ip}:{config.HY_PORT}?insecure=1&sni={config.HY_SNI}&obfs={config.HY_OBFS}&obfs-password={config.HY_OBFS}#{user}"
    
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

_Toca los códigos para copiarlos directamente._
"""
    bot.send_message(chat_id, msg, parse_mode="Markdown")

# --- SISTEMA TELÉMETRICO (Reemplazo Panel Web) ---

def show_server_stats(message):
    import psutil
    import shutil
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = shutil.disk_usage("/").percent
    
    # Intento de obtener usuarios online
    online = manager.run_command("netstat -antp | grep ESTABLISHED | grep -v '127.0.0.1' | wc -l") or "0"
    
    msg = f"""
📈 *ESTADO DEL SERVIDOR* 🛡️

⚙️ *CPU:* `{cpu}%`
🧠 *RAM:* `{ram}%`
💾 *Disco:* `{disk}%`
🌐 *Cuentas Online:* `{online}`

📅 *Fecha:* `{time.strftime('%Y-%m-%d %H:%M')}`
"""
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

if __name__ == "__main__":
    try:
        print("🚀 Bot Maximus Premium en ejecución...")
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ El Bot ha colapsado: {e}")
        time.sleep(10) # Evitar bucle infinito de reinicio rápido si hay error de red
