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
            self.client.settimeout(1.0) # Un poco más de tiempo para payloads densos
            client_buffer = b''
            
            # Recolectar Handshake con soporte para Multi-Host Split
            for _ in range(20): 
                try:
                    chunk = self.client.recv(BUFLEN)
                    if not chunk: break
                    client_buffer += chunk
                    
                    # Criterio de parada: Tener el token Y el cierre de la última parte
                    if b'MAX-' in client_buffer or b'X-Shield-Token:' in client_buffer:
                        if client_buffer.endswith(b'\r\n\r\n') or client_buffer.endswith(b'\n\n'):
                            break
                        # Si hay muchos datos, probablemente ya tenemos lo necesario
                        if len(client_buffer) > 2048: break
                except socket.timeout:
                    if len(client_buffer) > 0: break
                    else: continue
            
            if not client_buffer:
                self.client.close()
                return

            # --- VALIDACIÓN SHIELD (Ultra Deep Scan) ---
            is_valid = False
            found_host = None
            
            # Buscamos el token en cualquier parte del bloque HTTP
            if b'MAX-' in client_buffer:
                try:
                    # Extraer el primer token que encontremos (formato robusto)
                    token_part = client_buffer.split(b'MAX-')[1]
                    # Cortar en el próximo separador común de encabezados
                    token = token_part.split(b'\r')[0].split(b'\n')[0].split(b' ')[0].split(b';')[0].strip().decode('utf-8')
                    found_host = decrypt_token(token)
                    if found_host: is_valid = True
                except: pass

            if not is_valid and b'X-Shield-Token:' in client_buffer:
                try:
                    token = client_buffer.split(b'X-Shield-Token:')[1].split(b'\r\n')[0].strip().decode('utf-8')
                    found_host = decrypt_token(token)
                    if found_host: is_valid = True
                except: pass

            if not is_valid:
                self.client.send(RESPONSE_403)
                self.client.close()
                return

            # Responder Handshake WebSocket
            self.client.send(RESPONSE_WS)
            
            # Conexión al Backend (Dropbear/SSH)
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
