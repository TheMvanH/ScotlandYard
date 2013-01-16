import asynchat
import asyncore
import threading
import socket

HOST, PORT = "127.0.0.1", 9999
socket.setdefaulttimeout(10)

class RequestHandler(asynchat.async_chat):
    """A request handler based on async_chat, for an asynchronous client"""
    LINE_TERMINATOR = "\r\n"
    
    def __init__(self, ADDRESS, source):
        asynchat.async_chat.__init__(self)
        self.source             = source
        self.ibuffer            = ''
        self.set_terminator(self.LINE_TERMINATOR)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(ADDRESS)
        
    def collect_incoming_data(self, data):
        #print "collect_incoming_data: [%s]" % data
        self.ibuffer += data
        
    def found_terminator(self):
        #print "found_terminator"
        self.source.on_recv(self.ibuffer)
        self.ibuffer = ''
        
    def send_data(self, data):
        #print "sending: [%s]" % data
        self.push(data+self.LINE_TERMINATOR)
        
    def handle_close(self):
        self.source._disconnect()
        asynchat.async_chat.handle_close(self)
        
    def handle_connect(self):
        self.source._connect()

        
class Manager(object):
    """this object provides a high level interface to an asynchronous TCP handler client
    as input it will take the address which is being connected to in a HOST, PORT tupple.
    It needs to be subclassed in order to provide actual functionality
    the provided methods can be altered:
    Manager.on_recv(message) is called when a message is received from the server
    Manager.on_connect() is called when the client connects to the server
    Manager.on_disconnect() is called when the client disconnects from the server
    further, the provided methods exist
    Manager.disconnect() will disconnect the Manager from the server, and destroy the connection
    Manager.reconnect(ADDRESS=False) will reconnect the Manager to the server, or maybe another server
    Manager.send(message) will send a string to the server
    Manager.shutdown() will kill the connection, and then the Manager
    also, the following variables help
    self.ADDRESS is the address currently connected to
    self.client is the RequestHandler object
    self._connected indicates if a connection is currently active
    """
    def __init__(self, ADDRESS=(HOST,PORT)):
        self._connected = False
        self.ADDRESS = ADDRESS
        self.client = RequestHandler(self.ADDRESS, self)
        clientthread = threading.Thread(name='clientthread',target=asyncore.loop)
        clientthread.start()
        
    def on_recv(self, message):
        print message
        
    def reconnect(self,ADDRESS=False):
        if hasattr(self,'client'):
            del self.client #kill the last requesthandler, and try a new one
        self.connected = False
        if ADDRESS:
            self.ADDRESS = ADDRESS
        self.client = RequestHandler(self.ADDRESS, self)
        clientthread = threading.Thread(name='clientthread',target=asyncore.loop)
        clientthread.start()
        
    def disconnect(self):
        if self._connected:
            self.client.handle_close() #kill the connection
        
    def _connect(self):
        self._connected = True
        self.on_connect()
        
    def on_connect(self):
        print 'connected to the server'
        
    def _disconnect(self):
        self._connected = False
        self.on_disconnect()
    
    def on_disconnect(self):
        print 'disconnected from the server'
        
    def send(self, message):
        if self._connected:
            self.client.send_data(message.replace('\r\n','\n'))
        return self._connected
        
    def shutdown(self):
        if self._connected:
            self.client.handle_close()
        del self.client
        del self