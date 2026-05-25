#!/bin/bash
# Wrapper to start cloudflared and extract trycloudflare URL
LOG_FILE="/var/log/maximus_tunnel.log"
URL_FILE="/etc/MaximusVpsMx/cf_tunnel.url"

# Clean up old files
rm -f "$LOG_FILE" "$URL_FILE"

# Run a background monitoring loop
(
    for i in {1..30}; do
        if [ -f "$LOG_FILE" ]; then
            URL=$(grep -o 'https://[-a-zA-Z0-9]*\.trycloudflare\.com' "$LOG_FILE" | head -n 1)
            if [ -n "$URL" ]; then
                echo "$URL" > "$URL_FILE"
                break
            fi
        fi
        sleep 1
    done
) &

# Exec cloudflared so systemd tracks it directly
exec /usr/local/bin/cloudflared tunnel --url http://127.0.0.1:6767 > "$LOG_FILE" 2>&1
