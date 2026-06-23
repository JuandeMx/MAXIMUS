# -*- coding: utf-8 -*-
import socket, threading, select, sys, time

# Config
LISTENING_ADDR = '0.0.0.0'
if sys.argv[1:]:
    LISTENING_PORT = int(sys.argv[1])
else:
    LISTENING_PORT = 8081

if len(sys.argv) > 2:
    STATUS_TEXT = sys.argv[2]
else:
    STATUS_TEXT = "By MAXIMUS | ELITE"

BUFLEN = 16384
TIMEOUT = 60

# stack responses to satisfy HTTP Custom
RESPONSE = f'HTTP/1.1 200 {STATUS_TEXT}\r\nContent-length: 0\r\n\r\nHTTP/1.1 200 Connection established\r\n\r\n'.encode('utf-8')

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
        except:
            pass
        finally:
            self.running = False
            self.soc.close()

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
            self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

            # Receive headers from client
            client_buffer = b''
            r, _, _ = select.select([self.client], [], [], 0.5)
            if r:
                client_buffer = self.client.recv(BUFLEN)

            if len(client_buffer) == 0:
                return

            client_buffer = collect_headers(self.client, client_buffer, 5)

            # Parse target from CONNECT line or Host header
            hostPort = self.findHeader(client_buffer, 'Host')
            if not hostPort:
                # Fallback to parse from CONNECT method line: "CONNECT 127.0.0.1:1194 HTTP/1.1"
                try:
                    lines = client_buffer.decode('utf-8', errors='ignore').split('\r\n')
                    parts = lines[0].split(' ')
                    if len(parts) >= 2 and ':' in parts[1]:
                        hostPort = parts[1]
                except:
                    pass

            if not hostPort:
                # Default fallback
                hostPort = '127.0.0.1:1194'

            i = hostPort.find(':')
            if i != -1:
                port = int(hostPort[i+1:])
                host = hostPort[:i]
            else:
                host = '127.0.0.1'
                port = 1194

            target = socket.create_connection((host, port), timeout=3)
            target.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # Respond success to client
            self.client.sendall(RESPONSE)

            # Relay loop
            sockets = [self.client, target]
            while True:
                r, _, e = select.select(sockets, [], sockets, 3600)
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
    try:
        server = Server(LISTENING_ADDR, LISTENING_PORT)
        server.start()
        while True:
            time.sleep(2)
    except:
        pass
