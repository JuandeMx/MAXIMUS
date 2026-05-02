#!/usr/bin/env python3
import socket, threading, select, sys, time, os
try:
    import maximus_auth
except ImportError:
    # Si estamos en /etc/MaximusVpsMx/core/
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import maximus_auth

# MaximusVpsMx - Pure WebSocket Proxy (WS-EPRO Engine)
# Minimal, Async, High Performance.

if len(sys.argv) < 3:
    print("Uso: ws-epro.py <Listen_Port> <Backend_Port>")
    sys.exit(1)

LISTENING_PORT = int(sys.argv[1])
TARGET_PORT = int(sys.argv[2])
LISTENING_ADDR = '0.0.0.0'
BUFLEN = 131072

RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nServer: Maximus-WSEngine\r\n\r\n'

class Proxy(threading.Thread):
    def __init__(self, client_sock):
        threading.Thread.__init__(self)
        self.client = client_sock

    def run(self):
        target = None
        try:
            self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            try:
                self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 20)
                self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            except: pass
            
            self.client.settimeout(4.0)
            client_buffer = b''
            
            # Recolectar datos con tolerancia al [split] de HTTP Custom
            while True:
                try:
                    chunk = self.client.recv(BUFLEN)
                    if not chunk: break
                    client_buffer += chunk
                    # Si ya recibimos un doble salto de línea, rompemos el ciclo
                    if b'\r\n\r\n' in client_buffer or b'\n\n' in client_buffer:
                        break
                    # Si el payload usa un [split] malicioso sin \r\n\r\n, forzamos un chequeo HTTP temprano
                    if len(client_buffer) > 10 and b'HTTP/' in client_buffer:
                       if b'Upgrade' in client_buffer or b'\n' in client_buffer:
                          break 
                except socket.timeout:
                    if len(client_buffer) > 0:
                        break
                    else:
                        return

            if not client_buffer:
                self.client.close()
                return

            if b'HTTP' in client_buffer:
                # --- Maximus Elite Validation ---
                headers_str = client_buffer.decode('utf-8', errors='ignore')
                ok, msg = maximus_auth.authenticate_elite(headers_str)
                if not ok:
                    err_msg = f"HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\n\r\nMaximus Auth Error: {msg}\r\n"
                    self.client.send(err_msg.encode())
                    self.client.close()
                    return

                # Responder con 101 Switching Protocols sin importar qué headers traiga (Payload Inyectado)
                self.client.send(RESPONSE_WS)
            
            # Conectar al backend con Fallback (Dropbear/OpenSSH)
            target = None
            ports_to_try = [TARGET_PORT]
            if TARGET_PORT == 22: ports_to_try.append(44)
            elif TARGET_PORT == 44: ports_to_try.append(22)
            
            for pt in ports_to_try:
                try:
                    target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    target.settimeout(3)
                    target.connect(('127.0.0.1', pt))
                    target.setblocking(1)
                    break
                except:
                    if target:
                        target.close()
                    target = None
                    
            if not target:
                self.client.close()
                return

            self.client.setblocking(1)

            # Extraer y enviar el cuerpo remanente si existiera
            body_start = client_buffer.find(b'\r\n\r\n')
            if body_start != -1 and len(client_buffer) > body_start + 4:
                # Comprobar que no estemos enviando headers HTTP crudos al SSH si fue un Payload Ofuscado con split
                if b'SSH-' not in client_buffer[body_start + 4:]:
                     pass # Probablemente restos de un Payload agresivo, se ignoran.
                else:
                     target.send(client_buffer[body_start + 4:])
            elif b'HTTP' not in client_buffer:
                target.send(client_buffer)

            sockets = [self.client, target]
            running_relay = True
            is_first_data = True
            while running_relay:
                try:
                    # Timeout de 2 horas para inactividad extrema (7200s)
                    r, _, e = select.select(sockets, [], sockets, 7200)
                    if not r or e: break 
                    
                    for sock in r:
                        data = sock.recv(BUFLEN)
                        if not data: 
                            running_relay = False
                            break
                        
                        out = target if sock is self.client else self.client

                        # --- FILTRO ANTIGOLPE (v4.6 Universal) ---
                        if is_first_data and sock is self.client:
                            if (b'HTTP/' in data or b'Host:' in data or b'COPY ' in data or b'GET ' in data or b'POST ' in data or b'X /' in data) and b'SSH-' not in data:
                                continue 
                            
                            is_first_data = False
                            if b'SSH-' in data:
                                data = data[data.find(b'SSH-'):]
                                
                        out.sendall(data)
                except:
                    break
                    
        except Exception:
            pass
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

def main():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((LISTENING_ADDR, LISTENING_PORT))
        server.listen(1024)
        print(f"WS-EPRO iniciado en Puerto {LISTENING_PORT} -> Backend {TARGET_PORT}")
        while True:
            c, _ = server.accept()
            p = Proxy(c)
            p.daemon = True
            p.start()
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
