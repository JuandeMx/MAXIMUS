# MaximusVpsMx 🇲🇽

Panel de gestión VPS profesional para túneles SSH/SSL con soporte UDP para juegos.

## ⚡ Instalación en Una Línea

```bash
apt-get install -y git && git clone https://github.com/JuandeMx/MAXIMUS.git /tmp/MaximusVpsMx && cd /tmp/MaximusVpsMx && chmod +x install.sh && bash install.sh
```

> **Requisitos:** Ubuntu 20.04 / 22.04 / 24.04 LTS · Acceso root · Puertos 22, 44, 80, 443, 7300 libres

## 🔧 Características

| Módulo | Descripción | Puerto |
|--------|------------|--------|
| **Dropbear SSH** | Servidor SSH ligero optimizado para túneles | 44 |
| **Proxy Inteligente** | Anti-fragmentación TCP para redes 3G/4G | 80 |
| **Stunnel SSL** | Túnel SSL con TCP_NODELAY | 443 |
| **BadVPN UDPGW** | Soporte UDP para juegos y llamadas | 7300 |
| **Cloudflare DDNS** | Actualización automática de IP dinámica | — |
| **Firewall UFW** | Protección de puertos automatizada | — |

## 📱 Compatible con

- HTTP Custom
- HTTP Injector
- HA Tunnel Plus
- Cualquier cliente SSH/SSL

## 🎮 Uso

```bash
MX
```

### Menú Principal
```
[1] 👤 Usuarios y Sesiones
[2] 🔌 Opciones de Protocolo (Proxy, SSL, UDP)
[3] ⚙️  Sistema, Backups y Seguridad
[0] Salir
```

## ☁️ Cloudflare DDNS

Actualiza automáticamente tu IP en Cloudflare cada 5 minutos:

```
MX → [3] Sistema → [6] Cloudflare DDNS → [1] Configurar
```

Solo necesitas: **API Token**, **Zone ID** y **Dominio**.

## 🔒 Seguridad

- Solo `root` puede ejecutar el panel
- Usuarios de túnel creados con `/bin/false` (sin acceso a terminal)
- Permisos `700/600` en todos los archivos del sistema
- Firewall UFW preconfigurado

## 🗑️ Desinstalación

Desde el panel:

```
MX → [3] Sistema → [99] Desinstalador Maestro
```

## 📄 Licencia

Uso privado. MaximusVpsMx © 2024-2026
