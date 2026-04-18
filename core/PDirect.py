import socket, threading, select, sys, time, datetime, os

# MaximusVpsMx - Universal Agnostic Proxy Core v5.1 (Stable Rebuild)
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 80
BUFLEN = 8192
TIMEOUT = 120

# Respuestas Estándar
RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nServer: Maximus-Agnostic\r\n\r\n'
RESPONSE_STD = b'HTTP/1.1 200 Connection Established\r\nServer: Maximus-Agnostic\r\n\r\n'

def log_msg(msg):
    try:
        with open("/var/log/MaximusVpsMx/proxy.log", "a") as f:
            f.write(f"[{datetime.datetime.now()}] {msg}\n")
    except: pass

class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.running = False

    def run(self):
        try:
            self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.soc.bind((self.host, self.port))
            self.soc.listen(128)
            self.running = True
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    ConnectionHandler(c, addr).start()
                except: continue
        except Exception as e:
            log_msg(f"Server Error: {e}")
        finally:
            self.running = False

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient, addr):
        threading.Thread.__init__(self)
        self.client = socClient
        self.client.settimeout(TIMEOUT)
        self.addr = addr
        self.daemon = True

    def run(self):
        target = None
        try:
            # --- MOTOR HÍBRIDO AGNÓSTICO (Peeking) ---
            # Esperamos datos iniciales del cliente
            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 0.5)
            if r:
                client_buffer = self.client.recv(BUFLEN)
            
            if not client_buffer:
                self.client.close()
                return

            # Clasificación de Tráfico (Motor Agnóstico v5.2)
            is_ssh = client_buffer.startswith(b'SSH-')
            
            # Buscamos si el buffer contiene una estructura HTTP (Verbo + Path + HTTP/)
            is_http = False
            if not is_ssh:
                # Si contiene "HTTP/" es casi seguro una petición web
                if b'HTTP/' in client_buffer:
                    is_http = True
                # O si empieza con verbos comunes de payloads (incluyendo COPY)
                elif any(client_buffer.startswith(v) for v in [b'GET', b'POST', b'HEAD', b'CONNECT', b'COPY', b'PUT', b'DELETE', b'OPTIONS', b'PROPFIND']):
                    is_http = True
            
            # --- GESTIÓN DE PROTOCOLOS ---
            if is_http:
                # Anti-Fragmentación: Esperar cabeceras completas
                deadline = time.time() + 3
                while b'\r\n\r\n' not in client_buffer and b'\n\n' not in client_buffer:
                    if time.time() > deadline: break
                    r, _, _ = select.select([self.client], [], [], 0.5)
                    if r:
                        chunk = self.client.recv(BUFLEN)
                        if not chunk: break
                        client_buffer += chunk
                    else: break
                
                # Respuesta Automática (Simulando Proxy/WS)
                if b'upgrade: websocket' in client_buffer.lower():
                    self.client.sendall(RESPONSE_WS)
                else:
                    self.client.sendall(RESPONSE_STD)
                
                # Pequeña pausa para sincronización
                time.sleep(0.05)

            # --- CONEXIÓN AL BACKEND ---
            # Buscamos puerto dropbear
            drop_port = 44
            try:
                if os.path.exists('/etc/default/dropbear'):
                    with open('/etc/default/dropbear', 'r') as f:
                        for line in f:
                            if 'DROPBEAR_PORT=' in line:
                                drop_port = int(line.split('=')[1].strip().strip('"'))
            except: pass

            ports = [drop_port, 22, 2222, 110, 143]
            for p in ports:
                try:
                    target = socket.create_connection(('127.0.0.1', p), timeout=2)
                    target.settimeout(TIMEOUT)
                    break
                except: continue
            
            if not target:
                self.client.close()
                return

            # --- RELAY BIDIRECCIONAL ---
            if is_ssh:
                # Directo: Enviamos el buffer original
                target.sendall(client_buffer)
            elif is_http:
                # HTTP: Filtramos cabeceras si es necesario o enviamos el sobrante
                idx = client_buffer.find(b'\r\n\r\n')
                if idx != -1:
                    leftover = client_buffer[idx+4:]
                    if leftover: target.sendall(leftover)
            else:
                # SSL / Desconocido: Envío transparente
                target.sendall(client_buffer)

            # Transmisión Full-Duplex
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
    print(f"Maximus Universal v5.1 iniciado en puerto: {LISTENING_PORT}")
    Server('0.0.0.0', LISTENING_PORT).run()
