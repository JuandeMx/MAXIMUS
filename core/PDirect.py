import socket, threading, select, sys, time, datetime

# Config
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 80
BUFLEN = 8192
TIMEOUT = 120
RESPONSE_CONTINUE = b'HTTP/1.1 100 Continue\r\n\r\n'
RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n'
RESPONSE_STD = b'HTTP/1.1 200 Connection Established\r\n\r\n'

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
            self.soc.listen(100)
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

def relay_stream(source, destination):
    """Relay bidireccional puro."""
    try:
        while True:
            data = source.recv(BUFLEN)
            if not data:
                break
            destination.sendall(data)
    except:
        pass
    finally:
        try: source.close()
        except: pass
        try: destination.close()
        except: pass

def collect_headers(sock, initial_buffer, timeout_sec):
    """Recolectar datos hasta encontrar fin de cabeceras HTTP doble CRLF."""
    buf = initial_buffer
    deadline = time.time() + timeout_sec
    while b'\r\n\r\n' not in buf and b'\n\n' not in buf:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        r, _, _ = select.select([sock], [], [], min(remaining, 0.5))
        if sock in r:
            chunk = sock.recv(BUFLEN)
            if not chunk:
                break
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

            # Recepción inicial: CloudFront puede mandar todo en el primer paquete
            client_buffer = self.client.recv(BUFLEN)
            if not client_buffer:
                return

            is_ssh = client_buffer.startswith(b'SSH-')

            if not is_ssh:
                # MODO PROXY HTTP / CLOUDFRONT
                # Recolectar cabeceras completas (soporta payloads largos y junk)
                client_buffer = collect_headers(self.client, client_buffer, 5)

                # Detección de Handshake WebSocket (Standard-compliant)
                is_ws = b'upgrade: websocket' in client_buffer.lower()
                is_split = b'100-continue' in client_buffer.lower()

                if is_split:
                    # Responder 100 Continue (Protocolo Split)
                    self.client.sendall(RESPONSE_CONTINUE)
                    # Esperar la segunda parte del payload
                    second_buffer = b''
                    second_buffer = collect_headers(self.client, second_buffer, 3)
                    
                    if b'websocket' in second_buffer.lower():
                        self.client.sendall(RESPONSE_WS)
                    else:
                        self.client.sendall(RESPONSE_STD)
                elif is_ws:
                    # Handshake directo para CloudFront / No-Split
                    self.client.sendall(RESPONSE_WS)
                else:
                    # Respuesta estandar para el resto
                    self.client.sendall(RESPONSE_STD)

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

            for port in [22, drop_port]:
                try:
                    target = socket.create_connection(('127.0.0.1', port), timeout=10)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    target.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    target.settimeout(TIMEOUT)
                    break
                except:
                    target = None
                    continue

            if not target:
                return

            # Manejo del flujo inicial
            if is_ssh:
                target.sendall(client_buffer)
            else:
                # Revisar si el saludo SSH quedó atrapado en el buffer tras el HTTP
                leftover = b''
                if b'\r\n\r\n' in client_buffer:
                    leftover = client_buffer.split(b'\r\n\r\n', 1)[1]
                elif b'\n\n' in client_buffer:
                    leftover = client_buffer.split(b'\n\n', 1)[1]

                # Modo Transparente: Si hay leftover, se envía. Si no, se entra a relay.
                if leftover:
                    target.sendall(leftover)

            # Iniciar Relay Bidireccional de alto rendimiento
            # En este punto el túnel está establecido y el relay es puro.
            t1 = threading.Thread(target=relay_stream, args=(self.client, target))
            t1.daemon = True
            t1.start()

            relay_stream(target, self.client)
            t1.join(timeout=5)

        except Exception as e:
            log_error(f"Error en ConnectionHandler: {e}")
        finally:
            try: self.client.close()
            except: pass
            try:
                if target: target.close()
            except: pass

def main():
    print(f"MaximusVpsMx Proxy v3.2 - AWS CloudFront Ready Edition\nListening on {LISTENING_PORT}")
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
