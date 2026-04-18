#!/bin/bash
# Instalador Dinámico SlowDNS (DNSTT)

echo -e "\e[1;36m=========================================================\e[0m"
echo -e "\e[1;33m             INSTALADOR SLOWDNS (Túnel DNS)\e[0m"
echo -e "\e[1;36m=========================================================\e[0m"
read -p " ¿En qué puerto público deseas recibir SlowDNS? (Tradicional: 53): " dns_port
if [[ -z "$dns_port" ]]; then dns_port=53; fi

read -p " ¿Hacia qué puerto local debe enviar los datos descubiertos? (ej: 22 ssh, 80 proxy): " fwd_port
if [[ -z "$fwd_port" ]]; then fwd_port=22; fi

read -p " ¿Qué dominio NS administrará la conexión? (ej: slow.vpsmx.store): " ns_dom
if [[ -z "$ns_dom" ]]; then ns_dom="slow.vpsmx.store"; fi

echo -e "\n\e[1;32m[+] Compilando e Instalando SlowDNS ($dns_port -> $fwd_port)...\e[0m"

# Liberar el puerto 53 (Evitar choque con systemd-resolved)
if [[ "$dns_port" == "53" ]]; then
    echo -e "\e[1;33m    → Liberando puerto 53 (Desactivando systemd-resolved)...\e[0m"
    systemctl stop systemd-resolved 2>/dev/null
    systemctl disable systemd-resolved 2>/dev/null
    rm -f /etc/resolv.conf
    echo "nameserver 8.8.8.8" > /etc/resolv.conf
    echo "nameserver 1.1.1.1" >> /etc/resolv.conf
fi

# Instalar Go si no existe
if ! command -v go &>/dev/null; then
    echo -e "\e[1;33m    → Instalando compilador Go...\e[0m"
    DEBIAN_FRONTEND=noninteractive apt-get install -y golang-go 2>/dev/null
fi

if [ ! -f /usr/local/bin/slowdns ]; then
    echo -e "\e[1;33m    → Descargando motor DNS Tunnel (dnstt) en C/Go...\e[0m"
    curl -sL -o /usr/local/bin/slowdns "https://github.com/JuandeMx/MAXIMUS/raw/main/bin/dnstt-server-linux-amd64"
    chmod +x /usr/local/bin/slowdns 2>/dev/null
fi

# Generar llaves Hexadecimales (x25519) reales para DNSTT
echo -e "\e[1;33m    → Generando llaves criptográficas x25519 (DNSTT Native)...\e[0m"
mkdir -p /etc/MaximusVpsMx/slowdns

if [ ! -f /etc/MaximusVpsMx/slowdns/server.key ]; then
    /usr/local/bin/slowdns -gen > /etc/MaximusVpsMx/slowdns/keys.txt
    grep "Private key:" /etc/MaximusVpsMx/slowdns/keys.txt | awk '{print $3}' > /etc/MaximusVpsMx/slowdns/server.key
    grep "Public key:" /etc/MaximusVpsMx/slowdns/keys.txt | awk '{print $3}' > /etc/MaximusVpsMx/slowdns/server.pub
    rm -f /etc/MaximusVpsMx/slowdns/keys.txt
fi

echo "$ns_dom" > /etc/MaximusVpsMx/slowdns/ns-domain.conf

# Crear servicio dinámico
cat > /etc/systemd/system/mx-slowdns.service << EOF
[Unit]
Description=MaximusVpsMx SlowDNS Tunnel
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/slowdns -udp :$dns_port -privkey-file /etc/MaximusVpsMx/slowdns/server.key $ns_dom 127.0.0.1:$fwd_port
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

ufw allow ${dns_port}/udp 2>/dev/null
ufw allow ${dns_port}/tcp 2>/dev/null
ufw allow 5353/tcp 2>/dev/null

systemctl daemon-reload
systemctl enable --now mx-slowdns 2>/dev/null
echo -e "\e[1;32m[✓] SlowDNS instalado y activo en puerto $dns_port.\e[0m"
sleep 3
