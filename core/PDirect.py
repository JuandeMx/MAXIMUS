# -*- coding: utf-8 -*-
import socket, threading, select, sys, time, os

# Optimizacion de recursos y memoria de hilos
try:
    threading.stack_size(256 * 1024)
except:
    pass

try:
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (max(soft, 65535), max(hard, 65535)))
except:
    pass

# Config
LISTENING_ADDR = '0.0.0.0'
if sys.argv[1:]:
    LISTENING_PORT = int(sys.argv[1])
else:
    LISTENING_PORT = 80

BUFLEN = 16384
TIMEOUT = 60
DEFAULT_HOST = '127.0.0.1:443'

def obtener_banner_chico():
    default_text = "MAXIMUS VPS"
    path = "/etc/MaximusVpsMx/core/small_banner.txt"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().strip().replace("\r", "").replace("\n", " ")
                if text:
                    return text
        except:
            pass
    return default_text

BANNER_TEXT = obtener_banner_chico()

RESPONSE_WS = f'HTTP/1.1 101 {BANNER_TEXT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n'.encode('utf-8')
RESPONSE_STD = f'HTTP/1.1 200 {BANNER_TEXT}\r\nContent-length: 0\r\n\r\n'.encode('utf-8')
RESPONSE_CONTINUE = b'HTTP/1.1 100 Continue\r\n\r\n'

def configure_socket(sock):
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'TCP_KEEPIDLE'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 20)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        if hasattr(socket, 'TCP_KEEPCNT'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except:
        pass

class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.daemon = True
        self.running = False
        self.host = host
        self.port = port
        self.soc = None

    def run(self):
        self.running = True
        while self.running:
            try:
                self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.soc.settimeout(2.0)
                self.soc.bind((self.host, self.port))
                self.soc.listen(256)
                break
            except Exception:
                time.sleep(2)
                if not self.running:
                    return

        while self.running:
            try:
                c, addr = self.soc.accept()
                c.setblocking(1)
            except socket.timeout:
                continue
            except (ConnectionAbortedError, ConnectionResetError, BlockingIOError, InterruptedError):
                continue
            except OSError:
                time.sleep(0.05)
                continue
            except Exception:
                time.sleep(0.05)
                continue

            try:
                conn = ConnectionHandler(c, addr)
                conn.daemon = True
                conn.start()
            except Exception:
                try:
                    c.close()
                except:
                    pass

        try:
            if self.soc:
                self.soc.close()
        except:
            pass

def collect_headers(sock, initial_buffer, timeout_sec):
    buf = initial_buffer
    deadline = time.time() + timeout_sec
    while b'\r\n\r\n' not in buf and b'\n\n' not in buf:
        remaining = deadline - time.time()
        if remaining <= 0: break
        r, _, _ = select.select([sock], [], [], min(remaining, 0.5))
        if sock in r:
            chunk = sock.recv(BUFLEN)
            if not chunk: break
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
            configure_socket(self.client)

            # Peeking the initial packet
            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 0.5)
            if r:
                client_buffer = self.client.recv(BUFLEN)

            if not client_buffer:
                return

            is_ssh = client_buffer.startswith(b'SSH-')
            is_payload = (not is_ssh) and (len(client_buffer) > 0)

            if is_payload:
                client_buffer = collect_headers(self.client, client_buffer, 5)
                is_ws = b'upgrade: websocket' in client_buffer.lower()
                is_split = b'100-continue' in client_buffer.lower()

                if is_split:
                    self.client.sendall(RESPONSE_CONTINUE)
                    second_buffer = b''
                    second_buffer = collect_headers(self.client, second_buffer, 3)
                    if b'websocket' in second_buffer.lower():
                        self.client.sendall(RESPONSE_WS)
                    else:
                        self.client.sendall(RESPONSE_STD)
                elif is_ws:
                    self.client.sendall(RESPONSE_WS)
                else:
                    self.client.sendall(RESPONSE_STD)
                
                time.sleep(0.05)

            # Parse backend from X-Real-Host if present, else fallback
            hostPort = ''
            if is_payload:
                hostPort = self.findHeader(client_buffer, 'X-Real-Host')
            
            if not hostPort:
                hostPort = DEFAULT_HOST

            i = hostPort.find(':')
            if i != -1:
                port = int(hostPort[i+1:])
                host = hostPort[:i]
            else:
                host = '127.0.0.1'
                port = 443

            if host == 'localhost':
                host = '127.0.0.1'

            target = socket.create_connection((host, port), timeout=3)
            configure_socket(target)

            # Send initial data to backend
            if is_ssh:
                target.sendall(client_buffer)
            elif is_payload:
                header_end = -1
                if b'\r\n\r\n' in client_buffer:
                    header_end = client_buffer.find(b'\r\n\r\n') + 4
                elif b'\n\n' in client_buffer:
                    header_end = client_buffer.find(b'\n\n') + 2
                
                if header_end != -1:
                    leftover = client_buffer[header_end:]
                    if leftover: target.sendall(leftover)

            # Relay loop con timeout de 300s para limpiar conexiones muertas
            sockets = [self.client, target]
            while True:
                r, _, e = select.select(sockets, [], sockets, 300)
                if not r or e: break
                for sock in r:
                    data = sock.recv(BUFLEN)
                    if not data: return
                    out = target if sock is self.client else self.client
                    out.sendall(data)

        except:
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

    def findHeader(self, head, header):
        try:
            if isinstance(head, bytes):
                head = head.decode('utf-8', errors='ignore')
            aux = head.find(header + ': ')
            if aux == -1: return ''
            aux = head.find(':', aux)
            head = head[aux+2:]
            aux = head.find('\r\n')
            if aux == -1: return ''
            return head[:aux]
        except:
            return ''

if __name__ == '__main__':
    server = Server(LISTENING_ADDR, LISTENING_PORT)
    server.start()
    while True:
        try:
            time.sleep(3)
            if not server.is_alive():
                server = Server(LISTENING_ADDR, LISTENING_PORT)
                server.start()
        except KeyboardInterrupt:
            server.running = False
            break
        except:
            time.sleep(2)

