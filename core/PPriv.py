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
    LISTENING_PORT = 8083

if len(sys.argv) > 2:
    STATUS_TEXT = sys.argv[2]
else:
    STATUS_TEXT = "By MAXIMUS | ELITE"

if len(sys.argv) > 3:
    ALLOWED_SERVER = sys.argv[3]
else:
    ALLOWED_SERVER = "127.0.0.1"

BUFLEN = 16384
TIMEOUT = 60

RESPONSE_OK = f'HTTP/1.1 200 {STATUS_TEXT}\r\nConnection: close\r\n\r\n'.encode('utf-8')
RESPONSE_FORBIDDEN = b'HTTP/1.1 403 Server Forbidden\r\nConnection: close\r\nContent-length: 16\r\n\r\nServer Forbidden'

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

            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 0.5)
            if r:
                client_buffer = self.client.recv(BUFLEN)

            if not client_buffer:
                return

            client_buffer = collect_headers(self.client, client_buffer, 5)

            # Parse target from CONNECT line or Host header
            hostPort = self.findHeader(client_buffer, 'Host')
            if not hostPort:
                try:
                    lines = client_buffer.decode('utf-8', errors='ignore').split('\r\n')
                    parts = lines[0].split(' ')
                    if len(parts) >= 2 and ':' in parts[1]:
                        hostPort = parts[1]
                except:
                    pass

            if not hostPort:
                hostPort = '127.0.0.1:22'

            i = hostPort.find(':')
            if i != -1:
                port = int(hostPort[i+1:])
                host = hostPort[:i]
            else:
                host = '127.0.0.1'
                port = 22

            # Private security check: host must match ALLOWED_SERVER or loopback
            is_allowed = False
            if host in ['127.0.0.1', 'localhost', '::1']:
                is_allowed = True
            elif ALLOWED_SERVER in host or host in ALLOWED_SERVER:
                is_allowed = True

            if not is_allowed:
                self.client.sendall(RESPONSE_FORBIDDEN)
                return

            if host == 'localhost':
                host = '127.0.0.1'

            target = socket.create_connection((host, port), timeout=3)
            configure_socket(target)

            # Respond success to client
            self.client.sendall(RESPONSE_OK)

            # Relay loop con timeout de 300s para limpiar conexiones zombi
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

