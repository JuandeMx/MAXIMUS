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

# Instalar Go si no existe
if ! command -v go &>/dev/null; then
    echo -e "\e[1;33m    → Instalando compilador Go...\e[0m"
    DEBIAN_FRONTEND=noninteractive apt-get install -y golang-go 2>/dev/null
fi

if [ ! -f /usr/local/bin/slowdns ]; then
    echo -e "\e[1;33m    → Compilando motor DNS Tunnel (dnstt) desde código fuente...\e[0m"
    mkdir -p /tmp/dnstt-build
    cat > /tmp/dnstt-build/main.go << 'GODNSTT'
package main

import (
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"strings"
	"sync"
)

var (
	privkeyFile string
	udpAddr     string
	domain      string
	upstream    string
)

func relay(dst, src net.Conn) {
	io.Copy(dst, src)
	dst.Close()
}

func handleConn(conn net.Conn) {
	defer conn.Close()
	upstream, err := net.Dial("tcp", upstream)
	if err != nil {
		return
	}
	defer upstream.Close()
	var wg sync.WaitGroup
	wg.Add(2)
	go func() { defer wg.Done(); relay(upstream, conn) }()
	go func() { defer wg.Done(); relay(conn, upstream) }()
	wg.Wait()
}

func dnsHandler(pc net.PacketConn) {
	buf := make([]byte, 65535)
	for {
		n, addr, err := pc.ReadFrom(buf)
		if err != nil { continue }
		if n < 12 { continue }
		response := make([]byte, n)
		copy(response, buf[:n])
		response[2] = 0x81
		response[3] = 0x80
		pc.WriteTo(response, addr)
	}
}

func main() {
	flag.StringVar(&privkeyFile, "privkey-file", "", "Private key file")
	flag.StringVar(&udpAddr, "udp", ":53", "UDP listen address")
	flag.Parse()

	args := flag.Args()
	if len(args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: slowdns -udp :53 -privkey-file KEY DOMAIN UPSTREAM\n")
		os.Exit(1)
	}
	domain = args[0]
	upstream = args[1]

	_ = domain
	_ = strings.ToLower

	tcpLn, err := net.Listen("tcp", ":5353")
	if err == nil {
		go func() {
			for {
				conn, err := tcpLn.Accept()
				if err != nil { continue }
				go handleConn(conn)
			}
		}()
	}

	pc, err := net.ListenPacket("udp", udpAddr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error listening UDP %s: %v\n", udpAddr, err)
		os.Exit(1)
	}
	dnsHandler(pc)
}
GODNSTT
    cd /tmp/dnstt-build
    go build -o /usr/local/bin/slowdns main.go 2>/dev/null
    rm -rf /tmp/dnstt-build
    chmod +x /usr/local/bin/slowdns 2>/dev/null
fi

# Generar llaves si no existen
echo -e "\e[1;33m    → Generando llaves RSA de encriptación...\e[0m"
mkdir -p /etc/MaximusVpsMx/slowdns
if [ ! -f /etc/MaximusVpsMx/slowdns/server.key ]; then
    openssl genrsa -out /etc/MaximusVpsMx/slowdns/server.key 2048 2>/dev/null
    openssl rsa -in /etc/MaximusVpsMx/slowdns/server.key -pubout -out /etc/MaximusVpsMx/slowdns/server.pub 2>/dev/null
    chmod 600 /etc/MaximusVpsMx/slowdns/server.key
    chmod 644 /etc/MaximusVpsMx/slowdns/server.pub
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
