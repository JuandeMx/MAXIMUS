#!/usr/bin/env python3
import socket, threading, select, sys, time, os, base64

# MAXIMUS-SHIELD v1.0 (Elite WebSocket Engine)
# Propietario: JuandeMx / MAXIMUS
# Características: SNI De-Obfuscation & Signature Validation.

if len(sys.argv) < 3:
    print("Uso: maximus-shield.py <Listen_Port> <Backend_Port>")
    sys.exit(1)

LISTENING_PORT = int(sys.argv[1])
TARGET_PORT = int(sys.argv[2])
LISTENING_ADDR = '0.0.0.0'
BUFLEN = 8192

# Cargar Llave Maestra de Cifrado
KEY_PATH = "/etc/MaximusVpsMx/shield.key"
SECRET_KEY = b"MAXIMUS_DEFAULT_KEY" # Fallback
if os.path.exists(KEY_PATH):
    with open(KEY_PATH, "rb") as f:
        SECRET_KEY = f.read().strip()

def xor_crypt(data, key):
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])

def decrypt_token(token):
    try:
        # Formato esperado: base64(xor(host, key))
        decoded = base64.b64decode(token)
        decrypted = xor_crypt(decoded, SECRET_KEY)
        return decrypted.decode('utf-8')
    except:
        return None

RESPONSE_WS = b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nServer: MAXIMUS-SHIELD-ENGINE\r\n\r\n'
RESPONSE_403 = b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\n\r\nShield Error: Connection Not Signed.'

class Proxy(threading.Thread):
    def __init__(self, client_sock):
        threading.Thread.__init__(self)
        self.client = client_sock

    def run(self):
        target = None
        try:
            self.client.settimeout(2.5)
            client_buffer = b''
            
            # Recolectar Handshake
            while True:
                try:
                    chunk = self.client.recv(BUFLEN)
                    if not chunk: break
                    client_buffer += chunk
                    if b'\r\n\r\n' in client_buffer or b'\n\n' in client_buffer: break
                except socket.timeout:
                    break

            if not client_buffer:
                self.client.close()
                return

            # --- VALIDACIÓN SHIELD ---
            # Buscamos el Token en los Headers (Host o X-Shield-Token)
            is_valid = False
            found_host = None
            
            # 1. Chequeo de Token X-Shield
            if b'X-Shield-Token:' in client_buffer:
                parts = client_buffer.split(b'X-Shield-Token:')
                if len(parts) > 1:
                    token = parts[1].split(b'\r\n')[0].strip().decode('utf-8')
                    found_host = decrypt_token(token)
                    if found_host: is_valid = True

            # 2. Chequeo de Host Ofuscado (Inicia con MAX-)
            if not is_valid and b'Host:' in client_buffer:
                parts = client_buffer.split(b'Host:')
                host_val = parts[1].split(b'\r\n')[0].strip().decode('utf-8')
                if host_val.startswith("MAX-"):
                    found_host = decrypt_token(host_val[4:])
                    if found_host: is_valid = True

            # Si no hay SHIELD, pero es un WebSocket estándar, permitimos solo si no es modo estricto
            # (En Maximus-Shield somos estrictos por defecto para elitismo)
            if not is_valid:
                self.client.send(RESPONSE_403)
                self.client.close()
                return

            # Responder Handshake WebSocket
            self.client.send(RESPONSE_WS)
            
            # Conexión al Backend
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.settimeout(3)
            target.connect(('127.0.0.1', TARGET_PORT))
            target.setblocking(1)
            self.client.setblocking(1)

            # Bridging
            sockets = [self.client, target]
            while True:
                r, _, _ = select.select(sockets, [], [], 120)
                if not r: break
                
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
        while True:
            c, _ = server.accept()
            p = Proxy(c)
            p.daemon = True
            p.start()
    except Exception as e:
        sys.exit(1)

if __name__ == '__main__':
    main()
