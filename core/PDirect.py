import socket, threading, select, sys, time, datetime

# Config
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 80
BUFLEN = 131072
TIMEOUT = 120

# Mensajes de Respuesta (Edición Suprema)
BANNER_SUPREMO = b'Server: AXOLOT-SUPREMACY\r\n'
RESPONSE_CONTINUE = b'HTTP/1.1 100 Continue\r\n' + BANNER_SUPREMO + b'\r\n'
RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n' + BANNER_SUPREMO + b'\r\n'
RESPONSE_STD = b'HTTP/1.1 200 OK\r\n' + BANNER_SUPREMO + b'\r\n'

class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.running = False
        self.host = host
        self.port = port

    def run(self):
        try:
            self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.soc.settimeout(2)
            self.soc.bind((self.host, self.port))
            self.soc.listen(200)
            self.running = True
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                except socket.timeout:
                    continue
                conn = ConnectionHandler(c, addr)
                conn.daemon = True
                conn.start()
        except Exception as e:
            log_error(f"Server error: {e}")
        finally:
            self.running = False
            self.soc.close()

    def close(self):
        self.running = False

def log_error(msg):
    try:
        with open("/var/log/MaximusVpsMx/proxy.log", "a") as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
    except:
        pass

def collect_headers(sock, initial_buffer, timeout_sec):
    buf = initial_buffer
    deadline = time.time() + timeout_sec
    while b'\r\n\r\n' not in buf and b'\n\n' not in buf:
        remaining = deadline - time.time()
        if remaining <= 0: break
        r, _, _ = select.select([sock], [], [], min(remaining, 0.5))
        if sock in r:
            chunk = sock.recv(BUFLEN)
            if not chunk: break
            buf += chunk
        else:
            break
    return buf

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient, addr):
        threading.Thread.__init__(self)
        self.client = socClient
        self.addr = addr

    def run(self):
        target = None
        try:
            self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            # KeepAlive Agresivo (Linux)
            try:
                self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 20)
                self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            except: pass

            # --- MOTOR HÍBRIDO v4.0 (Peeking) ---
            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 3.0)
            
            if r:
                client_buffer = self.client.recv(BUFLEN)
            
            # Decidimos el modo basado en lo que recibimos o en el silencio
            is_ssh = client_buffer.startswith(b'SSH-')
            is_payload = (not is_ssh) and (len(client_buffer) > 0)
            is_silent = len(client_buffer) == 0

            if is_payload:
                # MODO PROXY (HTTP / CLOUDFRONT / WEBSOCKET)
                client_buffer = collect_headers(self.client, client_buffer, 5)
                is_ws = b'upgrade: websocket' in client_buffer.lower()
                is_split = b'100-continue' in client_buffer.lower()

                if is_split:
                    self.client.sendall(RESPONSE_CONTINUE)
                    second_buffer = b''
                    second_buffer = collect_headers(self.client, second_buffer, 3)
                    if b'websocket' in second_buffer.lower():
                        self.client.sendall(RESPONSE_WS)
                    else:
                        self.client.sendall(RESPONSE_STD)
                elif is_ws:
                    self.client.sendall(RESPONSE_WS)
                else:
                    self.client.sendall(RESPONSE_STD)
                
                # Sincronización pequeña para separar cabeceras del flujo SSH
                time.sleep(0.1)

            # Conexión al Backend local (OpenSSH 22 o Dropbear paramétrico)
            drop_port = 44
            try:
                import os
                if os.path.exists('/etc/default/dropbear'):
                    with open('/etc/default/dropbear', 'r') as f:
                        for line in f:
                            if line.startswith('DROPBEAR_PORT='):
                                drop_port = int(line.split('=')[1].strip())
            except: pass

            for port in [drop_port, 22, 2222]:
                try:
                    target = socket.create_connection(('127.0.0.1', port), timeout=3)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    target.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    try:
                        target.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 20)
                        target.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                        target.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
                    except: pass
                    break
                except: continue

            if not target:
                self.client.close()
                return

            # Manejo del flujo inicial
            if is_ssh:
                target.sendall(client_buffer)
            elif is_payload:
                header_end = -1
                if b'\r\n\r\n' in client_buffer:
                    header_end = client_buffer.find(b'\r\n\r\n') + 4
                elif b'\n\n' in client_buffer:
                    header_end = client_buffer.find(b'\n\n') + 2
                
                if header_end != -1:
                    leftover = client_buffer[header_end:]
                    if leftover: target.sendall(leftover)

            # --- RELAY BIDIRECCIONAL SELECT ENGINE ---
            sockets = [self.client, target]
            running_relay = True
            while running_relay:
                try:
                    r, _, e = select.select(sockets, [], sockets, 30)
                    if e: break
                    for sock in r:
                        data = sock.recv(BUFLEN)
                        if not data: 
                            running_relay = False
                            break
                        
                        out = target if sock is self.client else self.client
                        out.sendall(data)
                except (socket.error, Exception):
                    break

        except Exception as e:
            log_error(f"Handler error ({self.addr}): {e}")
        finally:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
            except: pass
            try: 
                if target:
                    target.shutdown(socket.SHUT_RDWR)
                    target.close()
            except: pass

if __name__ == '__main__':
    print(f"Maximus Universal Agnostic iniciado en puerto: {LISTENING_PORT}")
    try:
        Server('0.0.0.0', LISTENING_PORT).run()
    except KeyboardInterrupt:
        pass
