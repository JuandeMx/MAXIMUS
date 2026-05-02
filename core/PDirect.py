import socket, threading, select, sys, time

# Maximus Proxy Engine v5.0 (Agnostic Supreme)
# Rediseñado para estabilidad total con payloads complejos

LISTENING_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 80
BUFLEN = 65536

class ConnectionHandler(threading.Thread):
    def __init__(self, socClient):
        threading.Thread.__init__(self)
        self.client = socClient

    def run(self):
        target = None
        try:
            self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # 1. Leer ráfaga inicial del Payload
            self.client.settimeout(3)
            try:
                data = self.client.recv(BUFLEN)
            except:
                data = b''
            
            if b'HTTP/' in data:
                # 2. Responder con éxito instantáneo
                if b'websocket' in data.lower():
                    resp = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nServer: Maximus\r\n\r\n'
                else:
                    resp = b'HTTP/1.1 200 OK\r\nServer: Maximus\r\n\r\n'
                self.client.sendall(resp)
                
                # 3. Limpiar basura extra (Anti-Split)
                # Drenamos cualquier ráfaga extra del payload antes de tocar el SSH
                time.sleep(0.05)
                self.client.setblocking(False)
                try:
                    while True:
                        if not self.client.recv(BUFLEN): break
                except: pass
                self.client.setblocking(True)

            # 4. Conexión al Backend (Agnóstico: busca 22, 44 o 2222)
            # Prioridad OpenSSH (22) para máxima compatibilidad
            backend_ports = [22, 44, 2222]
            # Intentar detectar el puerto real de Dropbear si existe
            try:
                import os
                if os.path.exists('/etc/default/dropbear'):
                    with open('/etc/default/dropbear', 'r') as f:
                        for line in f:
                            if line.startswith('DROPBEAR_PORT='):
                                dp = int(line.split('=')[1].strip())
                                if dp not in backend_ports: backend_ports.insert(0, dp)
            except: pass

            for port in backend_ports:
                try:
                    target = socket.create_connection(('127.0.0.1', port), timeout=2)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    break
                except: continue

            if not target:
                self.client.close()
                return

            # 5. Relay Bidireccional de Alta Velocidad
            sockets = [self.client, target]
            while True:
                r, _, e = select.select(sockets, [], sockets, 60)
                if e: break
                for sock in r:
                    payload = sock.recv(BUFLEN)
                    if not payload: return
                    
                    if sock is self.client:
                        target.sendall(payload)
                    else:
                        self.client.sendall(payload)

        except:
            pass
        finally:
            try: self.client.close()
            except: pass
            try: target.close()
            except: pass

class Server:
    def __init__(self, port):
        self.port = port

    def run(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        soc.bind(('0.0.0.0', self.port))
        soc.listen(500)
        while True:
            c, addr = soc.accept()
            ConnectionHandler(c).start()

if __name__ == '__main__':
    try:
        Server(LISTENING_PORT).run()
    except KeyboardInterrupt:
        sys.exit(0)
