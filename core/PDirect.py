import socket, threading, select, sys, time

# Maximus Proxy Engine v5.1 (Agnostic Elite)
# Optimizado para Payloads Complejos (POLL, COPY, Split, Instant-Split)

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
            
            # 1. Peering inicial del Payload
            self.client.settimeout(3)
            try:
                data = self.client.recv(BUFLEN)
            except:
                data = b''
            
            is_ssh = data.startswith(b'SSH-')
            
            if not is_ssh and len(data) > 0:
                # 2. Responder según el payload
                if b'websocket' in data.lower():
                    resp = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nServer: Maximus\r\n\r\n'
                else:
                    resp = b'HTTP/1.1 200 OK\r\nServer: Maximus\r\n\r\n'
                self.client.sendall(resp)

            # 3. Conexión al Backend (Agnóstico)
            backend_ports = [22, 44, 2222]
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

            # 4. Relay con Filtro de Ráfagas (v5.1)
            sockets = [self.client, target]
            is_first_client_packet = True
            
            # Si era SSH directo, mandamos el primer paquete
            if is_ssh:
                target.sendall(data)
                is_first_client_packet = False

            while True:
                r, _, e = select.select(sockets, [], sockets, 60)
                if e: break
                for sock in r:
                    payload = sock.recv(BUFLEN)
                    if not payload: return
                    
                    if sock is self.client:
                        # FILTRO DE RÁFAGAS: Limpiar basura de [split] y [instant_split]
                        if is_first_client_packet:
                            # Si es basura de payload (POLL, COPY, X /, etc), la ignoramos
                            if (b'HTTP/' in payload or b'Host:' in payload or b'POLL ' in payload or b'COPY ' in payload or b'X /' in payload or b'CONNECT ' in payload) and b'SSH-' not in payload:
                                continue
                            
                            # Si encontramos el SSH-, limpiamos y activamos el paso total
                            is_first_client_packet = False
                            if b'SSH-' in payload:
                                payload = payload[payload.find(b'SSH-'):]
                        
                        target.sendall(payload)
                    else:
                        # Datos del Servidor al Cliente (Banner SSH, etc) siempre pasan
                        self.client.sendall(payload)

        except:
            pass
        finally:
            try: self.client.close()
            except: pass
            try: target.close()
            except: pass

if __name__ == '__main__':
    try:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        soc.bind(('0.0.0.0', LISTENING_PORT))
        soc.listen(500)
        while True:
            c, _ = soc.accept()
            ConnectionHandler(c).start()
    except:
        sys.exit(0)
