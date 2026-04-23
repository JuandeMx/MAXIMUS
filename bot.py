import telebot
from telebot import types
import core.manager as manager
import core.database as db
import config
import os
import time
import psutil
import subprocess

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

def get_active_service_ports():
    try:
        output = subprocess.check_output("netstat -tuln", shell=True).decode()
        active = []
        if ":443 " in output: active.append("SSL: `443`")
        if ":80 " in output: active.append("SSH: `80`")
        if ":7300 " in output: active.append("BadVPN: `7300`")
        if ":7200 " in output: active.append("BadVPN: `7200`")
        if ":44 " in output: active.append("Dropbear: `44`")
        if ":1194 " in output: active.append("OpenVPN: `1194`")
        if ":36712 " in output: active.append("UDP-Custom: `36712`")
        return ", ".join(active) if active else "Ninguno detectado"
    except:
        return "Desconocido"

@bot.message_handler(commands=['crear'])
def handle_crear_comando(message):
    try:
        parts = message.text.split()
        if len(parts) != 4:
            bot.reply_to(message, "❌ *Uso incorrecto.*\n\n*Formato:* `/crear <usuario> <contraseña> <dias>`\n*Ejemplo:* `/crear maria 121341 30`", parse_mode="Markdown")
            return
            
        _, user, pw, days_str = parts
        days = int(days_str)
        
        bot.send_chat_action(message.chat.id, 'typing')
        success, result = manager.create_ssh_user(user, pw, days=days)
        
        if success:
            ip = config.HOST_DOMAIN if config.HOST_DOMAIN else manager.get_server_ip()
            active_ports = get_active_service_ports()
            msg = f"""✅ *Usuario Premium creado con exito*

🌐 *IP:* `{ip}`
👤 *USER:* `{user}`
🔑 *PASS:* `{pw}`
📅 *VENCE:* `{result}`

📋 *Para copiar directamente:*

🛡️ *SSL:*
`{ip}:443@{user}:{pw}`

🌐 *SSH 80:*
`{ip}:80@{user}:{pw}`

📡 *UDP Custom:*
`{ip}:{config.UDP_RANGE}@{user}:{pw}`

⚡ *Todos los puertos que estén activos:*
{active_ports}
"""
            bot.reply_to(message, msg, parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ *Error al crear:* {result}", parse_mode="Markdown")
            
    except ValueError:
        bot.reply_to(message, "❌ El parámetro <dias> debe ser un número entero.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error del sistema: {e}")

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    item_free = types.InlineKeyboardButton("🆓 Prueba Gratis (3d)", callback_data="get_free")
    item_buy = types.InlineKeyboardButton("💎 Comprar Premium", callback_data="buy_premium")
    item_stats = types.InlineKeyboardButton("📊 Estadísticas", callback_data="show_stats")
    item_support = types.InlineKeyboardButton("🆘 Soporte", url="https://t.me/TuSoporte")
    
    markup.add(item_free, item_buy)
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
    elif call.data == "buy_premium":
        show_buy_menu(call)
    elif call.data == "get_stats":
        show_server_stats(call.message.chat.id, call.from_user.id)
    elif call.data == "show_stats":
        show_server_stats(call.message.chat.id, call.from_user.id)
    elif call.data == "start":
        send_welcome(call.message)
    elif call.data.startswith("approve_"):
        _, client_id, username, password = call.data.split("_")
        process_admin_approval(call, client_id, username, password)
    elif call.data.startswith("pay_"):
        send_stars_invoice(call)
    elif call.data.startswith("renew_ads_"):
        process_renew_ads(call)

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

# --- SISTEMA DE PAGOS (TELEGRAM STARS) ---

def show_buy_menu(call):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"⚡ Standard (7 días) - {config.PRICE_7_DAYS} ⭐", callback_data="pay_7_days"))
    kb.add(types.InlineKeyboardButton(f"💎 Premium (30 días) - {config.PRICE_30_DAYS} ⭐", callback_data="pay_30_days"))
    kb.add(types.InlineKeyboardButton("⬅️ Volver", callback_data="start"))
    
    msg = """
*💎 SELECCIONA TU PLAN PREMIUM* 🚀
━━━━━━━━━━━━━━━━━━━━
Obtén acceso ilimitado a nuestros servidores de alta velocidad.

🔹 *Beneficios:*
• Sin anuncios.
• Soporte prioritario.
• Conexión ultra estable.
• Acceso a todos los protocolos.
━━━━━━━━━━━━━━━━━━━━
_Precios expresados en Telegram Stars (XTR)._
"""
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)

def send_stars_invoice(call):
    plan = call.data.replace("pay_", "")
    
    if plan == "7_days":
        title = "Maximus Standard (7 días)"
        desc = "Acceso Standard por una semana a nuestros servidores SSH/VPN."
        price = config.PRICE_7_DAYS
        payload = "plan_7_days"
    else:
        title = "Maximus Premium (30 días)"
        desc = "Acceso Premium completo por un mes a nuestra red Maximus Elite."
        price = config.PRICE_30_DAYS
        payload = "plan_30_days"
        
    bot.send_invoice(
        call.message.chat.id,
        title=title,
        description=desc,
        invoice_payload=payload,
        provider_token="", # Vacío para Telegram Stars
        currency="XTR",
        prices=[types.LabeledPrice(label="Stars", amount=price)],
        start_parameter="maximus-premium"
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def handle_payment_success(message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    username_tg = message.from_user.username
    
    days = 7 if "7_days" in payload else 30
    
    bot.send_message(user_id, "✅ *PAGO PROCESADO CON ÉXITO* 🌟\n\nGenerando tus credenciales...", parse_mode="Markdown")
    
    username = manager.generate_random_user()
    password = manager.generate_random_pass()
    
    success, expiry = manager.create_ssh_user(username, password, days=days)
    if success:
        db.update_trial(user_id, username_tg, username)
        deliver_account(user_id, username, password, expiry)
    else:
        bot.send_message(user_id, "❌ Error al crear la cuenta tras el pago. Por favor contacta a soporte.")

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
