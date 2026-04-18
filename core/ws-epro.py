#!/usr/bin/env python3
import socket, threading, select, sys, time, os

# MaximusVpsMx - WS-Engine Stable v6.1 (Auth-Free Edition)
# Este motor es una tubería pura de WebSockets para máxima compatibilidad.

if len(sys.argv) < 3:
    print("Uso: ws-epro.py <Listen_Port> <Backend_Port>")
    sys.exit(1)

LISTENING_PORT = int(sys.argv[1])
TARGET_PORT = int(sys.argv[2])
LISTENING_ADDR = '0.0.0.0'
BUFLEN = 8192

RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n'

class Proxy(threading.Thread):
    def __init__(self, client_sock):
        threading.Thread.__init__(self)
        self.client = client_sock
        self.daemon = True

    def run(self):
        target = None
        try:
            self.client.settimeout(3)
            client_buffer = b''
            
            # Captura de Handshake
            r, _, _ = select.select([self.client], [], [], 1.0)
            if r:
                client_buffer = self.client.recv(BUFLEN)
            
            if not client_buffer: return

            # Respondemos 101 de inmediato si parece HTTP
            if b'HTTP' in client_buffer:
                self.client.sendall(RESPONSE_WS)
            
            # Conexión al Backend
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.settimeout(3)
            target.connect(('127.0.0.1', TARGET_PORT))
            
            # Transmitir remanentes
            if b'HTTP' in client_buffer:
                idx = client_buffer.find(b'\r\n\r\n')
                if idx != -1:
                    leftover = client_buffer[idx+4:]
                    if leftover: target.sendall(leftover)
            else:
                target.sendall(client_buffer)

            # Relay Stream (Agnóstico)
            sockets = [self.client, target]
            while True:
                r, _, _ = select.select(sockets, [], [], 120)
                if not r: break
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

def main():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((LISTENING_ADDR, LISTENING_PORT))
        server.listen(1024)
        print(f"WS-Engine v6.1 activo: {LISTENING_PORT} -> {TARGET_PORT}")
        while True:
            c, _ = server.accept()
            Proxy(c).start()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
