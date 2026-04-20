# 🔥 MAXIMUS ELITE VPS - v7.3 Premium Master Release 🇲🇽

**Maximus Elite** es un panel de administración ultra-ligero y avanzado para servidores VPS bajo Linux (Ubuntu 20.04/24.04). Su objetivo es facilitar la implementación, gestión y venta automatizada de túneles VPN (SSH, SSL, UDP, Hysteria v2) a gran escala.

## 🚀 Instalación en Una Línea (Panel Principal)

Copia y pega este comando en tu terminal como usuario `root`. Esto instalará toda la base del panel, limpiará tu sistema y dejará todo listo.

```bash
apt-get update -y && apt-get install -y git && rm -rf /tmp/MaximusVpsMx && git clone https://github.com/JuandeMx/MAXIMUS.git /tmp/MaximusVpsMx && cd /tmp/MaximusVpsMx && chmod +x install.sh && bash install.sh
```

**⚠️ AVISO IMPORTANTE:** Ya no existe un comando separado para instalar el Bot. Todo el ecosistema de Maximus (incluido el Bot Premium) se instala directamente gestionando el servidor a través del panel principal.

Para entrar al panel, simplemente escribe cualquiera de estos comandos en tu consola:
👉 `menu` , `MENU` o `MX`

---

## 💎 Características Principales

### 🖥️ Panel Core (Consola)
- **Instalación Modular:** Servicios separados y estabilizados para alto tráfico.
- **Protocolos Activos:**
  - **SSH/Dropbear:** (Puerto 22 y 44)
  - **Stunnel4 (SSL):** Integración nativa para payloads en HTTP Custom (Puerto 443).
  - **UDP Custom:** Rango ultra rápido dedicado a gaming `7100-7200`.
  - **Hysteria v2:** Extracción dinámica de certificados y puertos con visualización de rango ancho (`2000-5000`).
  - **SlowDNS & BadVPN:** Soporte íntegro para conexiones con dominios Nameserver.
- **Auto-Defensa:** Configuración nativa de Firewall UFW.

---

### 🤖 Telegram Bot Master (Opcional - Gestor Integrado)
El panel cuenta con un gestor interactivo directamente desde Telegram para vender sin que estés despierto:

- **Instalación:** Vía el comando `MX` > `[3] Ajustes de Sistema` > `[7] Gestor Telegram Bot`.
- **🚀 Maximus Pay (Novedad):** Venta directa automatizada aceptando **Telegram Stars (XTR)**.
  - Planes auto-gestionados de 7 y 30 días.
  - Entrega del usuario y contraseña automática al completar el pago en la app.
- **🎬 Renovación por Anuncios:** Cuentas gratis (Trial) que pueden auto-renovarse por 24h mediante una interfaz simulada de 5 anuncios interactivos.
- **🛡️ Data Tracking:** Persistencia en SQLite vinculando el ID de Telegram del cliente con su usuario de Hysteria y SSH.
- **📊 Telemetría en Tiempo Real:** Los clientes pueden ver si su usuario está activo y cuántos días les quedan. Tú puedes ver el % de CPU y RAM.
- **Link Inteligente:** Generación inmediata de formatos listos para importar: HTTP Custom (Directo/SSL), UDP (Host:Port) y enlace `hy2://` exacto.

## 📱 Compatibilidad de Clientes
Diseñado para brillar en aplicaciones Android e iOS como:
- HTTP Custom
- HTTP Injector
- V2Ray / NekoBox (Para Hysteria)
- OpenVPN

---
**Disclaimer:** *Proyecto privado. Creado para la administración eficiente y robusta de redes.* MaximusVpsMx © 2026.
