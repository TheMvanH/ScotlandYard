import asynchat
import threading
import asyncore
import socket

HOST, PORT = "127.0.0.1", 9999
socket.setdefaulttimeout(10)
        
class RequestHandler(asynchat.async_chat):
    """A request handler based on async_chat, for an asynchronous server"""

    LINE_TERMINATOR = "\r\n"

    def __init__(self, conn_sock, client_address, server, id):
        asynchat.async_chat.__init__(self, conn_sock)
        self.server             = server
        self.client_address     = client_address
        self.ibuffer            = ''
        self.ident              = id
        self.server.manager.connlist[self.ident] = self
        self.set_terminator(self.LINE_TERMINATOR)
        self.server.manager.on_join(self.ident)
        
    def collect_incoming_data(self, data):
        #print "collect_incoming_data: [%s]" % data
        self.ibuffer += data
        
    def found_terminator(self):
        #print "found_terminator"
        self.server.manager.on_recv(self.ident, self.ibuffer)
        self.ibuffer = ''
        
    def send_data(self, data):
        #print "sending: [%s]" % data
        self.push(data+self.LINE_TERMINATOR)
        
    def handle_close(self):
        #print "conn_closed: client_address=%s:%s" % \
        #             (self.client_address[0],
        #              self.client_address[1])
        if self.ident in self.server.manager.connlist:
            self.server.manager.on_leave(self.ident)
            del self.server.manager.connlist[self.ident]
        asynchat.async_chat.handle_close(self)
        
class chatserver(asyncore.dispatcher):
    """a server dispatcher based on asyncore.dispatcher. It assigns each connection an unique ID and adds it to a manager connlist dict
    """
    allow_reuse_address         = False
    request_queue_size          = 5
    address_family              = socket.AF_INET
    socket_type                 = socket.SOCK_STREAM


    def __init__(self, address, handlerClass=RequestHandler, managerobj = object()):
        self.address            = address
        self.handlerClass       = handlerClass

        asyncore.dispatcher.__init__(self)
        self.create_socket(self.address_family,
                               self.socket_type)

        if self.allow_reuse_address:
            self.set_resue_addr()

        self.server_bind()
        self.server_activate()
        self.manager = managerobj
        self.unique_id_value = 0
        print "chatserver is running"
        
    def unique_id(self):
        if self.unique_id_value == 2**16:
            self.unique_id_value = 0
        self.unique_id_value+=1
        return self.unique_id_value-1

    def server_bind(self):
        self.bind(self.address)

    def server_activate(self):
        self.listen(self.request_queue_size)

    def fileno(self):
        return self.socket.fileno()

    def serve_forever(self):
        asyncore.loop()
    # TODO: try to implement handle_request()

    # Internal use
    def handle_accept(self):
        (conn_sock, client_address) = self.accept()
        if self.verify_request(conn_sock, client_address):
            self.process_request(conn_sock, client_address)


    def verify_request(self, conn_sock, client_address):
        return True


    def process_request(self, conn_sock, client_address):
        id = self.unique_id()
        self.handlerClass(conn_sock, client_address, self, id)
        
        print "conn_made: client_address=%s:%s at id=%s" % \
                     (client_address[0],
                      client_address[1],
                      id)


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
    
    def __init__(self, ADDRESS=(HOST,PORT)):
        self.ADDRESS = ADDRESS
        self.connlist = {}
        self.server = chatserver(self.ADDRESS,RequestHandler,self)
        serverthread = threading.Thread(name='server_thread',target=self.server.serve_forever)
        serverthread.start()
        
    def on_recv(self, id, message):
        print 'id=',id,'says: ',message
        
    def on_join(self, id):
        print 'id:', id, 'joined'
        
    def on_leave(self, id):
        print 'id:', id, 'left'
        
    def send(self, id, message):
        self.connlist[id].send_data(message.replace('\r\n','\n'))
        
    def sendall(self, message):
        [self.send(id,message) for id in self.connlist]
        # for id in self.connlist:
        #     self.send(id, message)
            
    def kick(self, id):
        self.connlist[id].handle_close()
            
    def shutdown(self):
        temp = []
        for id in self.connlist:
            temp.append(self.connlist[id])
        for connection in temp:
            connection.handle_close()
        self.server.handle_close()
        del self.server
        del self