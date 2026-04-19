import socket, threading, select, sys, time, datetime

# Config
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 80
BUFLEN = 8192
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

            # --- MOTOR HÍBRIDO v4.0 (Peeking) ---
            # Esperamos un breve momento para ver si el cliente habla (Payload)
            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 0.5)
            
            if r:
                client_buffer = self.client.recv(BUFLEN)
            
            # Decidimos el modo basado en lo que recibimos o en el silencio
            if not client_buffer:
                self.client.close()
                return

            # Clasificación de la conexión
            is_ssh = client_buffer.startswith(b'SSH-')
            is_http = any(client_buffer.startswith(v) for v in [b'GET ', b'POST ', b'HEAD ', b'CONNECT ', b'PUT ', b'DELETE ', b'OPTIONS ', b'TRACE ', b'PATCH ', b'PROPFIND '])
            
            # --- GESTIÓN DE PROTOCOLOS (PAYLOAD / WEBSOCKET) ---
            if is_http:
                # Anti-Fragmentación: Esperar cabeceras HTTP completas
                deadline = time.time() + 3
                while b'\r\n\r\n' not in client_buffer and b'\n\n' not in client_buffer:
                    if time.time() > deadline: break
                    r, _, _ = select.select([self.client], [], [], 0.5)
                    if r:
                        chunk = self.client.recv(BUFLEN)
                        if not chunk: break
                        client_buffer += chunk
                    else: break
                
                # Procesar Payload Split (100-continue)
                is_split = b'100-continue' in client_buffer.lower()
                if is_split:
                    self.client.sendall(b'HTTP/1.1 100 Continue\r\n\r\n')
                    second_buffer = b''
                    deadline = time.time() + 3
                    while b'\r\n\r\n' not in second_buffer and b'\n\n' not in second_buffer:
                        if time.time() > deadline: break
                        r, _, _ = select.select([self.client], [], [], 0.5)
                        if r:
                            chunk = self.client.recv(BUFLEN)
                            if not chunk: break
                            second_buffer += chunk
                        else: break
                    client_buffer += second_buffer

                # Enviar de vuelta la respuesta HTTP final esperada
                if b'upgrade: websocket' in client_buffer.lower():
                    self.client.sendall(RESPONSE_WS)
                else:
                    self.client.sendall(RESPONSE_STD)
                
                # Pequeña pausa para sincronización TCP
                time.sleep(0.05)

            # --- CONEXIÓN AL BACKEND ---
            # Buscamos puerto dropbear para no codificar '44' a fuego crudo
            drop_port = 44
            try:
                if os.path.exists('/etc/default/dropbear'):
                    with open('/etc/default/dropbear', 'r') as f:
                        for line in f:
                            if 'DROPBEAR_PORT=' in line:
                                drop_port = int(line.split('=')[1].strip().strip('"'))
            except: pass

            ports = [drop_port, 22, 2222]
            for p in ports:
                try:
                    target = socket.create_connection(('127.0.0.1', p), timeout=2)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    target.settimeout(TIMEOUT)
                    break
                except: continue
            
            if not target:
                self.client.close()
                return

            # --- RELAY BIDIRECCIONAL ---
            if is_ssh:
                # Bypass transparente
                target.sendall(client_buffer)
            elif is_http:
                # Evitar mandar la cabecera HTTP al demonio SSH, solo el payload útil remanente
                idx = client_buffer.find(b'\r\n\r\n')
                if idx != -1:
                    leftover = client_buffer[idx+4:]
                    if leftover: target.sendall(leftover)
            else:
                # Stunnel sin headers HTTP
                target.sendall(client_buffer)

            # Bucle de paso
            sockets = [self.client, target]
            while True:
                r, _, e = select.select(sockets, [], sockets, 60)
                if e: break
                for s in r:
                    data = s.recv(BUFLEN)
                    if not data: return
                    out = target if s is self.client else self.client
                    out.sendall(data)

        except: pass
        finally:
            try: self.client.close()
            except: pass
            try: target.close()
            except: pass

if __name__ == '__main__':
    print(f"Maximus Universal Agnostic iniciado en puerto: {LISTENING_PORT}")
    try:
        Server('0.0.0.0', LISTENING_PORT).run()
    except KeyboardInterrupt:
        pass
