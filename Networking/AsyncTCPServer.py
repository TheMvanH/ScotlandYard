import asynchat
import threading
import asyncore
import socket
import re
from hashlib import sha1
from base64 import b64encode

HOST, PORT = "127.0.0.1", 9999
socket.setdefaulttimeout(10)
        
class RequestHandler(asynchat.async_chat):
    """A request handler based on async_chat, for an asynchronous server"""

    LINE_TERMINATOR = "\r\n"

    def __init__(self, conn_sock, client_address, server, ident):
        asynchat.async_chat.__init__(self, conn_sock)
        self.server             = server
        self.client_address     = client_address
        self.ibuffer            = ''
        self.ident              = ident
        self.server.manager.connlist[self.ident] = self
        self.set_terminator(self.LINE_TERMINATOR)
        self.server.manager.on_join(self.ident, self.client_address)
        
    def collect_incoming_data(self, data):
        #print "collect_incoming_data: [%s]" % data
        self.ibuffer += data
        
    def found_terminator(self):
        #print "found_terminator"
        self.server.manager.on_recv(self.ident, self.ibuffer)
        self.ibuffer = ''
        
    def send_data(self, data, raw=False):
        #print "sending: [%s]" % data
        if raw:
            self.push(data)
        else:
            self.push(data+self.LINE_TERMINATOR)
        
    def handle_close(self):
        #print "conn_closed: client_address=%s:%s" % \
        #             (self.client_address[0],
        #              self.client_address[1])
        if self.ident in self.server.manager.connlist:
            self.server.manager.on_leave(self.ident)
            del self.server.manager.connlist[self.ident]
        asynchat.async_chat.handle_close(self)

class WebSocket(RequestHandler):
    """a requesthandler for websockets"""

    LINE_TERMINATOR = "\r\n\r\n"

    def __init__(self, conn_sock, client_address, server, ident):
        asynchat.async_chat.__init__(self, conn_sock)
        self.server             = server
        self.client_address     = client_address
        self.ibuffer            = ''
        self.ident              = ident
        self.server.manager.connlist[self.ident] = self
        self.set_terminator(self.LINE_TERMINATOR)
        self.server.manager.on_join(self.ident, self.client_address)
        self.state              = 'responseheader'

    def collect_incoming_data(self, data):
        #print "collect_incoming_data: [%s]" % data
        if self.state == 'responseheader':
            self.ibuffer += data
        else:
            #here follows the data decoding algorithm
            self.ibuffer += data
            if len(self.ibuffer)<6: #didn't get complete headers yet
                return
            elif self.ibuffer[0] != '\x81': #final transmission response header
                self.handle_close() #we don't like your kind of packets around here
            elif (ord(self.ibuffer[1]) & 127) <126:
                #packet of length <126, 2 chars of header, 4 mask, and self.ibuffer[1] & 127 length
                packlength = 6 + (ord(self.ibuffer[1]) & 127)
                if len(self.ibuffer)>=packlength:
                    self.handle_packet(self.ibuffer[2:6], self.ibuffer[6:packlength])
                    self.ibuffer = self.ibuffer[packlength:]
                    self.collect_incoming_data('')
                else:
                    return #packet not yet fully received
            elif len(self.ibuffer)<8: #header even larger
                return
            elif (ord(self.ibuffer[1]) & 127) == 126:
                packlength = 8 + int(self.ibuffer[2:4].encode('hex'),16)
                if len(self.ibuffer)>=packlength:
                    self.handle_packet(self.ibuffer[4:8], self.ibuffer[8:packlength])
                    self.ibuffer = self.ibuffer[packlength:]
                    self.collect_incoming_data('')
                else:
                    return #packet not yet fully received
            elif len(self.ibuffer)<14: #the header is even larger
                return
            elif(ord(self.ibuffer[1]) & 127) == 127:
                packlength = 14 + int(self.ibuffer[2:10].encode('hex'),16)
                if len(self.ibuffer)>=packlength:
                    self.handle_packet(self.ibuffer[10:14], self.ibuffer[14:packlength])
                    self.ibuffer = self.ibuffer[packlength:]
                    self.collect_incoming_data('')
                else:
                    return #packet not fully received yet
            else:
                self.handle_close() #nonconforming packet

    def handle_packet(self, key, data):
        #implements the actual decoding
        result = ''
        for i in range(len(data)):
            j = i % 4
            result += chr(ord(data[i]) ^ ord(key[j]))
        self.server.manager.on_recv(self.ident, result)
        
    def found_terminator(self):
        #print "found_terminator"
        message = self.ibuffer
        if self.state == 'responseheader': #we've received the upgrade request
            if re.search('GET \S+ HTTP/1[.]1',message) and 'Upgrade: websocket' in message:
                #print 'received request\n', message
                code = re.search('Sec-WebSocket-Key: (\S+)', message, re.I).group(1)
                code += '258EAFA5-E914-47DA-95CA-C5AB0DC85B11' #websocket magic key
                returncode = b64encode(sha1(code).digest())
                returnmessage = 'HTTP/1.1 101 WebSocket Protocol Handshake\r\nConnection: Upgrade\r\n\
Server: Scotland Yard\r\nUpgrade: websocket\r\nAccess-Control-Allow-Origin: %s\r\nAccess-Control-Allow-Credentials: true\r\n\
Sec-WebSocket-Accept: %s\r\nSec-WebSocket-Protocol: chat\r\nAccess-Control-Allow-Headers: content-type\r\n\r\n' % (self.server.address[0],returncode)
                #print 'sending headers\n', returnmessage
                self.ibuffer = ''
                self.state = 'binarytransfer'
                self.send_data(returnmessage, binary=False)
            else:
                self.handle_close() #not a websocket request, bugger off

    def send_data(self, data, binary=True):
        #print "sending: [%s]" % data
        if binary:
            #create the necessary data headers
            header = '\x81' #10000001
            if len(data)<126:
                header += chr(len(data))
            elif len(data) <= (2**16):
                header += '\x7e' #01111110
                header += ('0'*(6-len(hex(len(data))))+hex(len(data))[2:]).decode('hex')
            elif len(data) <= (2**64):
                header += '\x7f' #01111111
                header += ('0'*(10-len(hex(len(data))))+hex(len(data))[2:]).decode('hex')
            else: 
                raise Exception('No strings larger than 2 GB allowed. how the hell did you even')
            print header+data
            self.push(header+data)
        else:
            self.push(data)
        
class chatserver(asyncore.dispatcher):
    """a server dispatcher based on asyncore.dispatcher. It assigns each connection an unique ID and adds it to a manager connlist dict
    """
    allow_reuse_address         = False
    request_queue_size          = 5
    address_family              = socket.AF_INET
    socket_type                 = socket.SOCK_STREAM


    def __init__(self, address, managerobj, handlerClass=RequestHandler):
        self.address            = address
        self.handlerClass       = handlerClass

        asyncore.dispatcher.__init__(self)
        self.create_socket(self.address_family, self.socket_type)
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self.allow_reuse_address:
            self.set_resue_addr()
        self.bind(self.address)
        self.listen(self.request_queue_size)
        self.manager = managerobj
        self.unique_id_value = 0
        print "server is running"
        
    def unique_id(self):
        if self.unique_id_value == 2**16:
            self.unique_id_value = 0
        self.unique_id_value+=1
        return self.unique_id_value-1

    def serve_forever(self):
        try:
            asyncore.loop()
        except KeyboardInterrupt:
            print "killed by user"
            self.handle_close()
        except:
            print "uncaught python Exception in server loop"
            raise

    def handle_accept(self):
        print "connection being made"
        (conn_sock, client_address) = self.accept()
        if self.verify_request(conn_sock, client_address):
            self.process_request(conn_sock, client_address)

    def verify_request(self, conn_sock, client_address):
        return self.manager.allow_connect(client_address)

    def process_request(self, conn_sock, client_address):
        ident = self.unique_id()
        self.handlerClass(conn_sock, client_address, self, ident)
        print "conn_made: client_address=%s:%s at id=%s" % \
                     (client_address[0],
                      client_address[1],
                      ident)

    def handle_close(self):
        #print "closing the server"
        self.close()
        
   
class Manager(object):
    """this object provides a high level interface to an asynchronous TCP handler server
    as input it will take the address in a HOST, PORT tupple. 
    It needs to be subclassed to hook it into actual functionality.
    the provided methods can be altered:
    Manager.on_recv(id,message) is called on receiving a message
    Manager.on_join(id) is called on someone joining the server
    Manager.on_leave(id) is called when an id leaves the server
    Manager.allow_connect(client_address) is called when an ip tries to connect. return True to allow access
    futher, these methods are available to output
    Manager.send(id, message) will send a string to id
    Manager.sendall(message) will send a string to all connections
    Manager.kick(id) will break a connection
    Manager.shutdown() will break all connections, close the handlers, the server, and the Manager.
    Also the following variables exist
    self.connlist is a dictionary mapping of all active connection id's to their actual handler objects.
    self.server is the connection dispatcher based on asyncore.dispatcher
    self.ADDRESS is the server address
    """
    
    def __init__(self, ADDRESS=(HOST,PORT), requesthandler = RequestHandler):
        self.ADDRESS = ADDRESS
        self.connlist = {}
        self.requesthandler = requesthandler
        self.server = chatserver(self.ADDRESS, self, self.requesthandler)
        serverthread = threading.Thread(name='server_thread',target=self.server.serve_forever)
        serverthread.start()
        
    def on_recv(self, ident, message):
        print 'id=',ident,'says: ',message

    def allow_connect(self, client_address):
        return True
        
    def on_join(self, ident, client_address):
        print 'id:', ident, 'at', client_address, 'joined'
        
    def on_leave(self, ident):
        print 'id:', ident, 'left'
        
    def send(self, ident, message, raw=False):
        if (self.requesthandler == WebSocket):
            raw = True
        if not raw:
            message = message.replace('\r\n','\n')
        self.connlist[ident].send_data(message, raw)
        
    def sendall(self, message):
        [self.send(ident,message) for ident in self.connlist]
            
    def kick(self, ident):
        self.connlist[ident].handle_close()
            
    def shutdown(self):
        temp = []
        for ident in self.connlist:
            temp.append(self.connlist[ident])
        for connection in temp:
            connection.handle_close()
        self.server.handle_close()
        del self.server
        del self