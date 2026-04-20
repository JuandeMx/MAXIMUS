# MaximusVpsMx 🇲🇽 - Bot Edition v4.0

Gestión Premium de VPS para túneles SSH/SSL/UDP controlada 100% desde **Telegram**.

## 🚀 Instalación en Una Línea (Telegram Bot)

```bash
apt-get install -y git && git clone https://github.com/JuandeMx/MAXIMUS /etc/MaximusVpsMx && \
chmod +x /etc/MaximusVpsMx/modules/install_bot.sh && \
bash /etc/MaximusVpsMx/modules/install_bot.sh
```

> **Requisitos:** Ubuntu 20.04+ · Acceso root · Token de Bot (@BotFather).

## 🤖 Centro de Control (Bot Features)

| Comando | Función |
|---------|---------|
| `/stats` | Telemetría en tiempo real (CPU, RAM, Disco, Online). |
| `/free` | Generación automática de cuentas Trial (3 días) con cooldown antifraude. |
| `/premium` | Creación interactiva de cuentas personalizadas con aprobación del Admin. |
| `/menu` | Menú interactivo con botones para gestión rápida. |

## 🔧 Características Técnicas

- **Dropbear SSH:** Servidor ligero optimizado (Puerto 44).
- **Stunnel SSL:** Túneles seguros TLS (Puerto 443).
- **UDP Custom:** Protocolo optimizado para juegos.
- **Hysteria:** Soporte para rangos dinámicos.
- **SQLite Core:** Base de datos integrada para gestión de usuarios de Telegram.

## 📱 Compatible con
- HTTP Custom / Injector / V2Ray
- Cualquier cliente SSH/SSL/UDP

## 🛡️ Seguridad
- Acceso restringido por Telegram ID (Solo el Admin puede ejecutar comandos sensibles).
- Middleware antifraude para cuentas gratuitas (Bloqueo de 7 días por usuario).
- Usuarios SSH sin acceso a consola (`/bin/false`).

---
Uso privado. MaximusVpsMx © 2026
