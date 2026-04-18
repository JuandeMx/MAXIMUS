import socket, threading, select, sys, time, datetime, os
try:
    import maximus_auth
except:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import maximus_auth

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

            # --- MOTOR HÍBRIDO AGNÓSTICO v4.1 (Peeking Engine) ---
            # Esperamos datos iniciales. Un timeout de 0.5s es estándar.
            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 0.5)
            if r:
                client_buffer = self.client.recv(BUFLEN)
            
            # Clasificación de Tráfico
            is_ssh = client_buffer.startswith(b'SSH-')
            
            # Verificamos si es una estructura HTTP válida (NUEVO: Detección Agnóstica)
            http_verbs = [b'GET', b'POST', b'HEAD', b'CONNECT', b'PUT', b'DELETE', b'OPTIONS', b'PATCH']
            is_http = any(client_buffer.startswith(verb) for verb in http_verbs)
            
            # Si no es SSH ni HTTP claro, pero hay datos, es un Payload de Terceros o SSL.
            # En Maximus v4.1, si NO es HTTP claro, NO inyectamos respuestas para no romper el Bridge.
            
            if is_http:
                # --- PROCESAMIENTO MODO PROXY / WEBSOCKET ---
                client_buffer = collect_headers(self.client, client_buffer, 5)
                headers_str = client_buffer.decode('utf-8', errors='ignore')

                # Validación Elite (Opcional)
                if "X-User:" in headers_str:
                    ok, msg = maximus_auth.authenticate_elite(headers_str)
                    if not ok:
                        err_msg = f"HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\nServer: Maximus-Guard\r\n\r\nMaximus Auth Error: {msg}\r\n"
                        self.client.sendall(err_msg.encode())
                        self.client.close()
                        return

                # Manejo de respuestas automáticas (Solo para peticiones HTTP detectadas)
                if b'100-continue' in client_buffer.lower():
                    self.client.sendall(RESPONSE_CONTINUE)
                    time.sleep(0.1)
                
                # Respuesta de Conexión establecida (Motor Universal)
                if b'upgrade: websocket' in client_buffer.lower():
                    self.client.sendall(RESPONSE_WS)
                else:
                    # En lugar de enviar RESPONSE_STD inmediatamente, permitimos inyecciones de headers si se requiere.
                    # Por defecto enviamos el 200 OK para liberar el socket del cliente para el flujo SSH.
                    self.client.sendall(RESPONSE_STD)

                time.sleep(0.05)

            # --- BACKEND CONNECTION LOGIC ---
            drop_port = 44
            try:
                if os.path.exists('/etc/default/dropbear'):
                    with open('/etc/default/dropbear', 'r') as f:
                        for line in f:
                            if line.startswith('DROPBEAR_PORT='):
                                drop_port = int(line.split('=')[1].strip())
            except: pass

            backend_ports = [22, drop_port, 2222]
            
            # Detección de puerto destino inyectado en el path (ej: GET / HTTP/1.1 -> Host: 127.0.0.1:443)
            requested_port = None
            if is_http:
                # Buscar puerto en Host: o en la primera línea
                first_line = client_buffer.split(b'\n')[0]
                if b':' in first_line:
                    try: requested_port = int(first_line.split(b':')[1].split(b' ')[0])
                    except: pass
                
            if requested_port and requested_port not in backend_ports:
                backend_ports.insert(0, requested_port)

            for port in backend_ports:
                try:
                    target = socket.create_connection(('127.0.0.1', port), timeout=2)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    break
                except: continue

            if not target:
                self.client.close()
                return

            # --- BRIDGE TRANSPARENTE (Relay) ---
            # Si no es HTTP, pasamos el buffer inicial tal cual (SSH o Payload agnostic)
            if not is_http:
                target.sendall(client_buffer)
            else:
                # Si fue HTTP, el header ya se consumió con el 200 OK.
                # Pasamos solo lo que quede después de las cabeceras si lo hay.
                header_end = client_buffer.find(b'\r\n\r\n')
                if header_end != -1:
                    leftover = client_buffer[header_end+4:]
                    if leftover: target.sendall(leftover)

            sockets = [self.client, target]
            while True:
                r, _, e = select.select(sockets, [], sockets, 120)
                if e: break
                for sock in r:
                    data = sock.recv(BUFLEN)
                    if not data: return
                    out = target if sock is self.client else self.client
                    out.sendall(data)

        except Exception as e:
            log_error(f"Handler error: {e}")
        finally:
            try: self.client.close()
            except: pass
            try: 
                if target: target.close()
            except: pass

def main():
    print(f"MaximusVpsMx Universal Proxy v4.1 - AGNÓSTICO\nEscuchando en puerto: {LISTENING_PORT}")
    server = Server('0.0.0.0', LISTENING_PORT)
    server.start()
    while True:
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            server.close()
            break

if __name__ == '__main__':
    main()
