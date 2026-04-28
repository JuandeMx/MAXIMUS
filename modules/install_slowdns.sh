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

# Instalar Go moderno (1.21.6) asegurando compilación correcta
if ! command -v go &>/dev/null || [[ $(go version | awk '{print $3}' | sed 's/go//;s/\..*//') -lt 1 || $(go version | awk '{print $3}' | awk -F'.' '{print $2}') -lt 18 ]]; then
    echo -e "\e[1;33m    → Instalando compilador Go moderno (1.21.6)...\e[0m"
    cd /tmp
    wget -q https://go.dev/dl/go1.21.6.linux-amd64.tar.gz
    rm -rf /usr/local/go
    tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz
    rm -f go1.21.6.linux-amd64.tar.gz
    export PATH=$PATH:/usr/local/go/bin
    grep -q "/usr/local/go/bin" /etc/profile || echo "export PATH=\$PATH:/usr/local/go/bin" >> /etc/profile
fi

echo -e "\e[1;33m    → Instalando motor real DNSTT-Server desde fuente oficial...\e[0m"
rm -f /usr/local/bin/slowdns 2>/dev/null
rm -rf /tmp/dnstt-src
git clone https://www.bamsoftware.com/git/dnstt.git /tmp/dnstt-src 2>/dev/null || git clone https://github.com/www-dt/dnstt.git /tmp/dnstt-src 2>/dev/null
echo -e "\e[1;33m    → Compilando motor...\e[0m"
cd /tmp/dnstt-src/dnstt-server
go build -o /usr/local/bin/slowdns 2>/dev/null
rm -rf /tmp/dnstt-src
chmod +x /usr/local/bin/slowdns 2>/dev/null

# Generar llaves Hexadecimales (x25519) reales para DNSTT
echo -e "\e[1;33m    → Generando llaves criptográficas x25519 (DNSTT Native)...\e[0m"
mkdir -p /etc/MaximusVpsMx/slowdns

if [ ! -f /etc/MaximusVpsMx/slowdns/server.key ]; then
    /usr/local/bin/slowdns -gen-key -privkey-file /etc/MaximusVpsMx/slowdns/server.key -pubkey-file /etc/MaximusVpsMx/slowdns/server.pub
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
echo -e "\e[1;36m═════════════════════════════════════════════════════════\e[0m"
echo -e "\e[1;33m 🔑 TU LLAVE PÚBLICA (Cópiala a HTTP Custom / Injector):\e[0m"
if [ -f /etc/MaximusVpsMx/slowdns/server.pub ]; then
    echo -e "\e[1;37m    $(cat /etc/MaximusVpsMx/slowdns/server.pub)\e[0m"
else
    echo -e "\e[1;31m    Error: No se encontró la llave.\e[0m"
fi
echo -e "\e[1;33m 🌐 DOMINIO NS:\e[0m"
echo -e "\e[1;37m    $ns_dom\e[0m"
echo -e "\e[1;36m═════════════════════════════════════════════════════════\e[0m"
sleep 5
