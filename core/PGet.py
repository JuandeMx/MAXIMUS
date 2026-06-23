# -*- coding: utf-8 -*-
import sys, time, getopt, socket, threading, base64

# CONFIG
CONFIG_LISTENING = '0.0.0.0:8799'
CONFIG_PASS = 'pwd.pwd'

class Logger:
    logLock = threading.Lock()
    LOG_INFO = 1
    LOG_WARN = 2
    LOG_ERROR = 3

    def printWarn(self, log):
        self.log(log)

    def printInfo(self, log):
        self.log(log)

    def printError(self, log):
        self.log(log)

    def printLog(self, log, logLevel):
        if logLevel == Logger.LOG_INFO:
            self.printInfo('<-> ' + log)
        elif logLevel == Logger.LOG_WARN:
            self.printWarn('<!> ' + log)
        elif logLevel == Logger.LOG_ERROR:
            self.printError('<#> ' + log)

    def log(self, log):
        with Logger.logLock:
            sys.stdout.write(log + '\n')
            sys.stdout.flush()

class PasswordSet:
    FILE_EXEMPLE = 'master=passwd123\n127.0.0.1:22=pwd321;321pawd\n1.23.45.67:443=pass123'

    def __init__(self, masterKey=None):
        self.masterKey = masterKey

    def parseFile(self, fileName):
        isValid = False
        with open(fileName, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.readlines()

        content = [x.strip() for x in content]
        content = [item for item in content if not str(item).startswith('#')]

        if len(content) > 0:
            masterKey = content[0]
            if self.splitParam(masterKey, '=') is not None and masterKey.startswith('master'):
                self.masterKey = self.splitParam(masterKey, '=')[1]
            isValid = True
            self.map = dict()
            for v in content[1:]:
                hostAndPass = self.splitParam(v, '=')
                if hostAndPass is not None:
                    self.map[hostAndPass[0]] = hostAndPass[1].split(';')
        return isValid

    def isValidKey(self, key, target):
        valid = False
        if isinstance(key, bytes):
            try: key = key.decode('utf-8')
            except: pass
        if self.masterKey != key:
            if hasattr(self, 'map'):
                if target in self.map:
                    valid = key in self.map[target]
        else:
            valid = True
        return valid

    def splitParam(self, param, c):
        index = param.find(c)
        ret = None
        if index != -1:
            ret = []
            ret.append(param[0:index])
            ret.append(param[index+1:])
        return ret

class ClientRequest:
    MAX_LEN_CLIENT_REQUEST = 1024 * 100
    HEADER_CONTENT_LENGTH = 'Content-Length'
    HEADER_ACTION = 'X-Action'
    ACTION_CLOSE = 'close'
    ACTION_DATA = 'data'

    def __init__(self, socket):
        self.socket = socket
        self.readConent = False

    def parse(self):
        line = b''
        count = 0
        self.isValid = False
        self.data = None
        self.contentLength = None
        self.action = None

        while line != b'\r\n' and count < ClientRequest.MAX_LEN_CLIENT_REQUEST:
            line_bytes = self.readHttpLine()
            if line_bytes is None:
                break
            line = line_bytes
            line_str = line.decode('utf-8', errors='ignore')
            if line_str.startswith(ClientRequest.HEADER_ACTION):
                self.action = self.getHeaderVal(line_str)
                if self.action is not None:
                    if self.action == ClientRequest.ACTION_CLOSE or self.action == ClientRequest.ACTION_DATA:
                        self.isValid = True
            count += len(line)

        if self.readConent:
            if self.contentLength and 0 < self.contentLength < ClientRequest.MAX_LEN_CLIENT_REQUEST:
                self.data = self.readFully(self.contentLength)
        return self.isValid

    def readHttpLine(self):
        line = b''
        count = 0
        socket = self.socket
        b = socket.recv(1)
        if not b:
            return None
        while count < ClientRequest.MAX_LEN_CLIENT_REQUEST:
            count += 1
            line += b
            if b == b'\r':
                b = socket.recv(1)
                count += 1
                if not b:
                    break
                line += b
                if b == b'\n':
                    break
            b = socket.recv(1)
            if not b:
                break
        if not b:
            return None
        return line

    def getHeaderVal(self, header):
        ini = header.find(':')
        if ini == -1: return None
        ini += 2
        fim = header.find('\r\n')
        if fim == -1:
            header = header[ini:]
        return header[ini:fim]

    def readFully(self, n):
        count = 0
        data = b''
        while count < n:
            packet = self.socket.recv(n - count)
            if not packet:
                break
            count += len(packet)
            data += packet
        return data

class Client(threading.Thread):
    ACTION_DATA = 'data'
    BUFFER_SIZE = 16384

    def __init__(self, id, readSocket, target):
        super(Client, self).__init__()
        self.targetHostPort = target
        self.id = id
        self.readSocket = readSocket
        self.logger = Logger()
        self.isStopped = False
        self.onCloseFunction = None
        self.closeLock = threading.Lock()
        self.threadEndCount = 0
        self.writeSocket = None

    def connectTarget(self):
        aux = self.targetHostPort.find(':')
        host = self.targetHostPort[:aux]
        port = int(self.targetHostPort[aux + 1:])
        if host == 'localhost':
            host = '127.0.0.1'
        self.target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.target.connect((host, port))

    def run(self):
        try:
            self.connectTarget()
            request = ClientRequest(self.readSocket)
            request.readConent = False
            if not request.parse() or Client.ACTION_DATA != request.action:
                raise Exception('client sends invalid request')
            threadRead = ThreadRelay(self.readSocket, self.target, self.finallyClose)
            threadRead.logFunction = self.log
            threadRead.start()
            threadWrite = ThreadRelay(self.target, self.writeSocket, self.finallyClose)
            threadWrite.logFunction = self.log
            threadWrite.start()
        except Exception as e:
            self.log('connection error - ' + str(type(e)) + ' - ' + str(e), Logger.LOG_ERROR)
            self.close()

    def finallyClose(self):
        with self.closeLock:
            self.threadEndCount += 1
            if self.threadEndCount == 2:
                self.close()

    def close(self):
        if not self.isStopped:
            self.isStopped = True
            if hasattr(self, 'target'):
                try: self.target.close()
                except: pass
            if hasattr(self, 'writeSocket'):
                try: self.writeSocket.close()
                except: pass
            if hasattr(self, 'readSocket'):
                try: self.readSocket.close()
                except: pass
            self.onClose()
            self.log('closed', Logger.LOG_INFO)

    def onClose(self):
        if self.onCloseFunction is not None:
            self.onCloseFunction(self)

    def log(self, msg, logLevel):
        msg = 'Client ' + str(self.id) + ': ' + msg
        self.logger.printLog(msg, logLevel)

class ThreadRelay(threading.Thread):
    def __init__(self, readSocket, writeSocket, closeFunction=None):
        super(ThreadRelay, self).__init__()
        self.readSocket = readSocket
        self.writeSocket = writeSocket
        self.logFunction = None
        self.closeFuntion = closeFunction

    def run(self):
        try:
            while True:
                data = self.readSocket.recv(Client.BUFFER_SIZE)
                if not data:
                    break
                self.writeSocket.sendall(data)
            try:
                self.writeSocket.shutdown(socket.SHUT_WR)
            except:
                pass
        except Exception as e:
            if self.logFunction is not None:
                self.logFunction('threadRelay error: ' + str(type(e)) + ' - ' + str(e), Logger.LOG_ERROR)
        finally:
            if self.closeFuntion is not None:
                self.closeFuntion()

class AcceptClient(threading.Thread):
    MAX_QTD_BYTES = 5000
    HEADER_BODY = 'X-Body'
    HEADER_ACTION = 'X-Action'
    HEADER_TARGET = 'X-Target'
    HEADER_PASS = 'X-Pass'
    HEADER_ID = 'X-Id'
    ACTION_CREATE = 'create'
    ACTION_COMPLETE = 'complete'
    MSG_CONNECTION_CREATED = 'Created'
    MSG_CONNECTION_COMPLETED = 'Completed'
    ID_COUNT = 0
    ID_LOCK = threading.Lock()

    def __init__(self, socket, server, passwdSet=None):
        super(AcceptClient, self).__init__()
        self.server = server
        self.passwdSet = passwdSet
        self.socket = socket

    def run(self):
        needClose = True
        try:
            head = self.readHttpRequest()
            bodyLen = self.getHeaderVal(head, AcceptClient.HEADER_BODY)
            if bodyLen is not None:
                try: self.readFully(int(bodyLen))
                except ValueError: pass

            action = self.getHeaderVal(head, AcceptClient.HEADER_ACTION)
            if action is None:
                self.log('client sends no action header', Logger.LOG_WARN)
                self.socket.sendall(b'HTTP/1.1 400 NoActionHeader!\r\nServer: GetTunnelServer\r\n\r\n')
                return

            if action == AcceptClient.ACTION_CREATE:
                target = self.getHeaderVal(head, AcceptClient.HEADER_TARGET)
                if self.passwdSet is not None:
                    passwd = self.getHeaderVal(head, AcceptClient.HEADER_PASS)
                    try:
                        passwd = base64.b64decode(passwd.encode('utf-8'))
                    except:
                        passwd = None
                    if passwd is None or not self.passwdSet.isValidKey(passwd, target):
                        self.log('client sends wrong key', Logger.LOG_WARN)
                        self.socket.sendall(b'HTTP/1.1 403 Forbidden\r\nServer: GetTunnelServer\r\n\r\n')
                        return

                if target is not None and self.isValidHostPort(target):
                    id = self.generateId()
                    client = Client(id, self.socket, target)
                    client.onCloseFunction = self.server.removeClient
                    self.server.addClient(client)
                    response = ('HTTP/1.1 200 '+ AcceptClient.MSG_CONNECTION_CREATED + '\r\nServer: GetTunnelServer\r\nX-Id: ' + str(id) + '\r\nContent-Type: text/plain\r\nContent-Length: 0\r\nConnection: Keep-Alive\r\n\r\n').encode('utf-8')
                    self.socket.sendall(response)
                    self.log('connection created - ' + str(id), Logger.LOG_INFO)
                    needClose = False
                else:
                    self.log('client sends no valid target', Logger.LOG_WARN)
                    self.socket.sendall(b'HTTP/1.1 400 Target!\r\nServer: GetTunnelServer\r\n\r\n')

            elif action == AcceptClient.ACTION_COMPLETE:
                id = self.getHeaderVal(head, AcceptClient.HEADER_ID)
                if id is not None:
                    client = self.server.getClient(id)
                    if client is not None:
                        client.writeSocket = self.socket
                        self.log('connection completed - ' + str(id), Logger.LOG_INFO)
                        response = ('HTTP/1.1 200 ' + AcceptClient.MSG_CONNECTION_COMPLETED + '\r\nServer: GetTunnelServer\r\nConnection: Keep-Alive\r\n\r\n').encode('utf-8')
                        self.socket.sendall(response)
                        client.start()
                        needClose = False
                    else:
                        self.log('client try to complete non existing connection', Logger.LOG_WARN)
                        self.socket.sendall(b'HTTP/1.1 400 CreateFirst!\r\nServer: GetTunnelServer\r\n\r\n')
                else:
                    self.log('client sends no id header', Logger.LOG_WARN)
                    self.socket.sendall(b'HTTP/1.1 400 NoID!\r\nServer: GetTunnelServer\r\n\r\n')
            else:
                self.log('client sends invalid action', Logger.LOG_WARN)
                self.socket.sendall(b'HTTP/1.1 400 InvalidAction!\r\nServer: GetTunnelServer\r\n\r\n')
        except Exception as e:
            self.log('connection error - ' + str(type(e)) + ' - ' + str(e), Logger.LOG_ERROR)
        finally:
            if needClose:
                try: self.socket.close()
                except: pass

    def log(self, msg, logLevel):
        self.server.log(msg, logLevel)

    def readHttpRequest(self):
        request = ''
        linha = ''
        count = 0
        while linha != '\r\n' and count < AcceptClient.MAX_QTD_BYTES:
            linha_bytes = self.readHttpLine()
            if linha_bytes is None:
                break
            linha = linha_bytes.decode('utf-8', errors='ignore')
            request += linha
            count += len(linha)
        return request

    def readHttpLine(self):
        line = b''
        count = 0
        socket = self.socket
        b = socket.recv(1)
        if not b:
            return None
        while count < AcceptClient.MAX_QTD_BYTES:
            count += 1
            line += b
            if b == b'\r':
                b = socket.recv(1)
                count += 1
                if not b:
                    break
                line += b
                if b == b'\n':
                    break
            b = socket.recv(1)
            if not b:
                break
        if not b:
            return None
        return line

    def getHeaderVal(self, head, header):
        if not head.startswith('\r\n'):
            header = '\r\n' + header
        if not header.endswith(': '):
            header = header + ': '
        ini = head.find(header)
        if ini == -1: return None
        end = head.find('\r\n', ini+2)
        ini += len(header)
        if end == -1 or ini > end or ini >= len(head):
            return None
        return head[ini:end]

    def readFully(self, n):
        count = 0
        while count < n:
            packet = self.socket.recv(n - count)
            if not packet:
                break
            count += len(packet)

    def isValidHostPort(self, hostPort):
        aux = hostPort.find(':')
        if aux == -1 or aux >= len(hostPort) -1:
            return False
        try:
            int(hostPort[aux+1:])
            return True
        except ValueError:
            return False

    def generateId(self):
        with AcceptClient.ID_LOCK:
            AcceptClient.ID_COUNT += 1
            return AcceptClient.ID_COUNT

class Server(threading.Thread):
    def __init__(self, listening, passwdSet=None):
        super(Server, self).__init__()
        self.listening = listening
        self.passwdSet = passwdSet
        self.running = False
        self.logger = Logger()
        self.isStopped = False
        self.clientsLock = threading.Lock()
        self.clients = []

    def run(self):
        try:
            self.soc = socket.socket(socket.AF_INET)
            self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.soc.settimeout(2)
            host = self.listening[:self.listening.find(':')]
            port = int(self.listening[self.listening.find(':') + 1:])
            self.soc.bind((host, port))
            self.soc.listen(100)
            self.log('running on ' + self.listening, Logger.LOG_INFO)
            self.running = True
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                    self.log('opening connection - ' + str(addr), Logger.LOG_INFO)
                    self.acceptClient(c)
                except socket.timeout:
                    continue
        except Exception as e:
            self.log('connection error - ' + str(type(e)) + ' - ' + str(e), Logger.LOG_ERROR)
        finally:
            self.running = False
            self.close()

    def acceptClient(self, socket):
        accept = AcceptClient(socket, self, self.passwdSet)
        accept.start()

    def addClient(self, client):
        with self.clientsLock:
            self.clients.append(client)

    def removeClient(self, client):
        with self.clientsLock:
            if client in self.clients:
                self.clients.remove(client)

    def getClient(self, id):
        client = None
        with self.clientsLock:
            for c in self.clients:
                if str(c.id) == str(id):
                    client = c
                    break
        return client

    def close(self):
        if not self.isStopped:
            self.isStopped = True
            if hasattr(self, 'soc'):
                try: self.soc.close()
                except: pass
            with self.clientsLock:
                clientsCopy = self.clients[:]
            for c in clientsCopy:
                c.close()
            self.log('closed', Logger.LOG_INFO)

    def log(self, msg, logLevel):
        msg = 'Server: ' + msg
        self.logger.printLog(msg, logLevel)

def print_usage():
    sys.stdout.write('\nUsage  : python get.py -b listening -p pass\n')
    sys.stdout.write('Ex.    : python get.py -b 0.0.0.0:80 -p pass123\n')
    sys.stdout.write('       : python get.py -b 0.0.0.0:80 -p passFile.pwd\n\n')
    sys.stdout.write('___Password file ex.:___\n')
    sys.stdout.write(PasswordSet.FILE_EXEMPLE + '\n')
    sys.stdout.flush()

def parse_args(argv):
    global CONFIG_LISTENING
    global CONFIG_PASS
    try:
        opts, args = getopt.getopt(argv, "hb:p:", ["bind=", "pass="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_usage()
            sys.exit()
        elif opt in ('-b', '--bind'):
            CONFIG_LISTENING = arg
        elif opt in ('-p', '--pass'):
            CONFIG_PASS = arg

def main():
    sys.stdout.write('\n-->GetTunnelPy - Server v.25/06/2017\n')
    sys.stdout.write('-->Listening: ' + CONFIG_LISTENING + '\n')
    sys.stdout.flush()
    pwdSet = None

    if CONFIG_PASS is not None:
        import os
        if CONFIG_PASS.endswith('.pwd') and os.path.exists(CONFIG_PASS):
            pwdSet = PasswordSet()
            try:
                isValidFile = pwdSet.parseFile(CONFIG_PASS)
            except IOError as e:
                sys.stdout.write('--#Error reading file: ' + str(type(e)) + ' - ' + str(e) + '\n')
                sys.stdout.flush()
                sys.exit()
            if not isValidFile:
                sys.stdout.write('--#Error on parsing file!\n\n')
                sys.stdout.flush()
                print_usage()
                return
            sys.stdout.write('-->Pass file: ' + CONFIG_PASS + '\n\n')
        else:
            if len(CONFIG_PASS) > 0:
                sys.stdout.write('-->Pass     : yes\n\n')
                pwdSet = PasswordSet(CONFIG_PASS)
            else:
                sys.stdout.write('-->Pass     : no\n\n')
        sys.stdout.flush()

    server = Server(CONFIG_LISTENING)
    server.passwdSet = pwdSet
    server.start()

    while True:
        try:
            time.sleep(2)
        except KeyboardInterrupt:
            sys.stdout.write('<-> Stopping server...\n')
            sys.stdout.flush()
            server.running = False
            break

if __name__ == '__main__':
    parse_args(sys.argv[1:])
    main()
