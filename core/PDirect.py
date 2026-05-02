import socket, threading, select, sys, time, datetime

# Config
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 80
BUFLEN = 131072

# Mensajes de Respuesta (Ultra Shield v4.8)
BANNER_SUPREMO = b'Server: AXOLOT-SUPREMACY\r\n'
RESPONSE_STD = b'HTTP/1.1 200 OK\r\n' + BANNER_SUPREMO + b'\r\n'
RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n' + BANNER_SUPREMO + b'\r\n'

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
            pass
        finally:
            self.running = False
            self.soc.close()

def log_error(msg):
    pass

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient, addr):
        threading.Thread.__init__(self)
        self.client = socClient
        self.addr = addr

    def run(self):
        target = None
        try:
            self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # --- PEERING INICIAL ---
            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 1.0)
            if r:
                client_buffer = self.client.recv(BUFLEN)
            
            is_ssh = client_buffer.startswith(b'SSH-')
            
            if not is_ssh and len(client_buffer) > 0:
                # Responder instantáneamente para engañar a la app/compañía
                if b'websocket' in client_buffer.lower():
                    self.client.sendall(RESPONSE_WS)
                else:
                    self.client.sendall(RESPONSE_STD)

            # --- CONEXIÓN AL BACKEND ---
            # Priorizamos Dropbear (44) y luego OpenSSH (22)
            for port in [44, 22, 2222]:
                try:
                    target = socket.create_connection(('127.0.0.1', port), timeout=3)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    break
                except: continue

            if not target:
                self.client.close()
                return

            # --- RELAY ULTRA SHIELD (v4.8) ---
            sockets = [self.client, target]
            is_first_client_data = True
            
            # Si era SSH directo, mandamos el banner de una vez
            if is_ssh:
                target.sendall(client_buffer)
                is_first_client_data = False

            while True:
                r, _, e = select.select(sockets, [], sockets, 60)
                if e: break
                for sock in r:
                    data = sock.recv(BUFLEN)
                    if not data: return
                    
                    if sock is self.client:
                        # FILTRO AGRESIVO: Ignorar todo hasta ver SSH-
                        if is_first_client_data:
                            if b'SSH-' in data:
                                is_first_client_data = False
                                data = data[data.find(b'SSH-'):]
                                target.sendall(data)
                            continue # Si no es SSH, ignorar ráfaga
                        target.sendall(data)
                    else:
                        # Datos del Servidor al Cliente (Banner SSH, etc) siempre pasan
                        self.client.sendall(data)

        except:
            pass
        finally:
            try: self.client.close()
            except: pass
            try: target.close()
            except: pass

if __name__ == '__main__':
    Server('0.0.0.0', int(sys.argv[1]) if len(sys.argv) > 1 else 80).run()
