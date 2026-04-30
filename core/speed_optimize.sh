#!/bin/bash
# Maximus Elite - Speed & Stability Optimizer
# Optimiza el kernel y los límites del sistema para tráfico masivo VPN/Proxy

if [ "$EUID" -ne 0 ]; then
    echo "Se requieren privilegios de root."
    exit 1
fi

echo -e "\e[1;32m[+] Iniciando Optimización de Red y Sistema (Modo Bestia)...\e[0m"

# 1. Optimización del Kernel (Sysctl)
cat > /etc/sysctl.d/99-maximus-speed.conf << 'EOF'
# Optimización de Red para Servidores VPN/Proxy - Maximus Elite
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864
net.ipv4.tcp_mtu_probing = 1
net.ipv4.ip_local_port_range = 1024 65535
fs.file-max = 1000000
EOF

sysctl -p /etc/sysctl.d/99-maximus-speed.conf >/dev/null 2>&1

# 2. Límites de Descriptores de Archivos (Ulimit)
echo -e "\e[1;32m[+] Configurando Límites de Archivos (Ulimit 1M)...\e[0m"
cat > /etc/security/limits.d/99-maximus-limits.conf << 'EOF'
* soft nofile 1000000
* hard nofile 1000000
* soft nproc 1000000
* hard nproc 1000000
root soft nofile 1000000
root hard nofile 1000000
EOF

# Aplicar límites a la sesión actual
ulimit -n 1000000

# 3. Optimización de SSH (Capacidad de Conexión)
echo -e "\e[1;32m[+] Expandiendo capacidad de OpenSSH...\e[0m"
cat > /etc/ssh/sshd_config.d/03-maximus-limits.conf << 'EOF'
MaxStartups 100:30:200
MaxSessions 1000
EOF

systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null

echo -e "\e[1;36m[✓] Sistema optimizado para estabilidad total.\e[0m"
