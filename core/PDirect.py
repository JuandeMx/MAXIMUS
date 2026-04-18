import socket, threading, select, sys, time, datetime, os

# MaximusVpsMx - Universal Agnostic Proxy Core v6.0 (Stability First Rebuild)
# Este motor prioriza la estabilidad absoluta y la compatibilidad con payloads antiguos.
# ELIMINADA VALIDACIÓN ELITE PARA EVITAR BLOQUEOS 403.

LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 80
BUFLEN = 8192
TIMEOUT = 120

# Respuestas Estándar (Minimalistas)
RESPONSE_STD = b'HTTP/1.1 200 Connection Established\r\n\r\n'
RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n'

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
            self.soc.listen(256)
            self.running = True
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    ConnectionHandler(c, addr).start()
                except: continue
        except Exception as e:
            log_msg(f"Server Error on port {self.port}: {e}")
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
            # --- MOTOR HÍBRIDO AGNÓSTICO (Peeking v6.0) ---
            client_buffer = b''
            # Peeking inicial para diferenciar SSH de HTTP/SSL
            r, _, _ = select.select([self.client], [], [], 0.5)
            if r:
                client_buffer = self.client.recv(BUFLEN)
            
            if not client_buffer:
                self.client.close()
                return

            is_ssh = client_buffer.startswith(b'SSH-')
            
            # Detección de HTTP (Aceptamos cualquier verbo + Path + HTTP/)
            is_http = False
            if not is_ssh:
                if b'HTTP/' in client_buffer:
                    is_http = True

            if is_http:
                # Anti-Fragmentación: Esperar cabeceras completas \r\n\r\n
                deadline = time.time() + 3
                while b'\r\n\r\n' not in client_buffer and b'\n\n' not in client_buffer:
                    if time.time() > deadline: break
                    r, _, _ = select.select([self.client], [], [], 0.5)
                    if r:
                        chunk = self.client.recv(BUFLEN)
                        if not chunk: break
                        client_buffer += chunk
                    else: break
                
                # Respuesta Automática (Handshake)
                if b'upgrade: websocket' in client_buffer.lower():
                    self.client.sendall(RESPONSE_WS)
                else:
                    self.client.sendall(RESPONSE_STD)
                
                time.sleep(0.05) # Pequeño gap para split

            # --- CONEXIÓN AL BACKEND (Dropbear/SSH) ---
            # Autodetección de puerto dropbear
            drop_port = 44
            try:
                if os.path.exists('/etc/default/dropbear'):
                    with open('/etc/default/dropbear', 'r') as f:
                        for line in f:
                            if 'DROPBEAR_PORT=' in line:
                                drop_port = int(line.split('=')[1].strip().strip('"'))
            except: pass

            backend_ports = [drop_port, 22, 2222, 110, 143]
            for p in backend_ports:
                try:
                    target = socket.create_connection(('127.0.0.1', p), timeout=2)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    target.settimeout(TIMEOUT)
                    break
                except: continue
            
            if not target:
                self.client.close()
                return

            # --- TRANSMISIÓN DE DATOS ---
            if is_ssh:
                target.sendall(client_buffer)
            elif is_http:
                # Si hay datos de payload residuales después del handshake, los enviamos
                idx = client_buffer.find(b'\r\n\r\n')
                if idx != -1:
                    residue = client_buffer[idx+4:]
                    if residue: target.sendall(residue)
            else:
                # Desconocido / SSL: Envío transparente
                target.sendall(client_buffer)

            # Relay Stream (Dual Mode)
            sockets = [self.client, target]
            while True:
                r, _, _ = select.select(sockets, [], [], 120)
                if not r: break # Timeout
                for s in r:
                    data = s.recv(BUFLEN)
                    if not data: return
                    pair = target if s is self.client else self.client
                    pair.sendall(data)

        except: pass
        finally:
            try: self.client.close()
            except: pass
            try: target.close()
            except: pass

if __name__ == '__main__':
    # Lanzamiento robusto
    Server('0.0.0.0', LISTENING_PORT).run()
