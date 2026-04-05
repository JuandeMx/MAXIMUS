import socket, threading, select, sys, time

# Config
LISTENING_ADDR = '0.0.0.0'
LISTENING_PORT = 80
BUFLEN = 8192
TIMEOUT = 120
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
            print(f"Server error: {e}")
        finally:
            self.running = False
            self.soc.close()

    def close(self):
        self.running = False

def relay_stream(source, destination, label=""):
    """Relay bidireccional simple: lee de source, escribe en destination."""
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

            client_buffer = self.client.recv(BUFLEN)
            if not client_buffer: return

            is_ssh = client_buffer.startswith(b'SSH-')

            if not is_ssh:
                # Anti-Fragmentacion TCP (redes celulares 3G/4G)
                deadline = time.time() + 3
                while b'\r\n\r\n' not in client_buffer and b'\n\n' not in client_buffer:
                    remaining = deadline - time.time()
                    if remaining <= 0: break
                    r, _, _ = select.select([self.client], [], [], min(remaining, 1.0))
                    if self.client in r:
                        chunk = self.client.recv(BUFLEN)
                        if not chunk: break
                        client_buffer += chunk
                    else:
                        break

                # Responder al cliente
                if b'websocket' in client_buffer.lower():
                    self.client.sendall(RESPONSE_WS)
                else:
                    self.client.sendall(RESPONSE_STD)

            # Conectar a Dropbear (44) o fallback OpenSSH (22)
            target = None
            for port in [44, 22]:
                try:
                    target = socket.create_connection(('127.0.0.1', port), timeout=10)
                    target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    target.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    target.settimeout(TIMEOUT)
                    break
                except:
                    target = None
                    continue

            if target is None:
                return

            # Modo SSH puro: reenviar el handshake original
            if is_ssh:
                target.sendall(client_buffer)

            # Relay bidireccional con DOS hilos independientes
            # Hilo 1: Cliente → Servidor (SSH)
            t1 = threading.Thread(target=relay_stream, args=(self.client, target, "C>S"))
            t1.daemon = True
            t1.start()

            # Hilo 2 (este hilo): Servidor (SSH) → Cliente
            relay_stream(target, self.client, "S>C")

            # Esperar a que el otro hilo termine
            t1.join(timeout=5)

        except Exception as e:
            try:
                with open("/var/log/MaximusVpsMx/proxy.log", "a") as f:
                    import datetime
                    f.write(f"[{datetime.datetime.now()}] Error: {e}\n")
            except: pass
        finally:
            try: self.client.close()
            except: pass
            try:
                if target: target.close()
            except: pass

def main():
    print("MaximusVpsMx Proxy - Puerto 80 [Dual Thread Relay]")
    server = Server('0.0.0.0', 80)
    server.start()
    while True:
        try: time.sleep(2)
        except KeyboardInterrupt:
            server.close()
            break

if __name__ == '__main__':
    main()
