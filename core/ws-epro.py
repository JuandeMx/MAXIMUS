#!/usr/bin/env python3
import socket, threading, select, sys, time

# MaximusVpsMx - Pure WebSocket Proxy (WS-EPRO Engine)
# Minimal, Async, High Performance.

if len(sys.argv) < 3:
    print("Uso: ws-epro.py <Listen_Port> <Backend_Port>")
    sys.exit(1)

LISTENING_PORT = int(sys.argv[1])
TARGET_PORT = int(sys.argv[2])
LISTENING_ADDR = '0.0.0.0'
BUFLEN = 8192

RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nServer: Maximus-WSEngine\r\n\r\n'

class Proxy(threading.Thread):
    def __init__(self, client_sock):
        threading.Thread.__init__(self)
        self.client = client_sock

    def run(self):
        target = None
        try:
            self.client.settimeout(2.0)
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
                # Responder con 101 Switching Protocols sin importar qué headers traiga (Payload Inyectado)
                self.client.send(RESPONSE_WS)
            
            # Conectar al backend (Dropbear/OpenSSH)
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.settimeout(3)
            target.connect(('127.0.0.1', TARGET_PORT))
            target.setblocking(1)
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
            while True:
                r, _, _ = select.select(sockets, [], [], 120)
                if not r: break # Timeout
                
                if self.client in r:
                    data = self.client.recv(BUFLEN)
                    if not data: break
                    target.sendall(data)
                    
                if target in r:
                    data = target.recv(BUFLEN)
                    if not data: break
                    self.client.sendall(data)
                    
        except Exception:
            pass
        finally:
            self.client.close()
            if target: target.close()

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
