#chatserver
import AsyncTCPServer

#serverIO = AsyncTCPServer.Manager()

class Manager(AsyncTCPServer.Manager):
    def on_recv(self, id, msg):
        print id,msg
        if msg.lower().strip() == 'ping':
            self.send(id,'PONG!')
        else:
            for idd in self.connlist:
                if idd is not id:
                    self.send(idd,msg)
                    
serverIO = None
                    
def run(ADDRESS = [('192.168.2.15',9999), ('192.168.2.15',9998), ('192.168.2.15',9997)],requesthandler = [AsyncTCPServer.RequestHandler, AsyncTCPServer.WebSocket, AsyncTCPServer.RequestHandler]):
    global serverIO
    serverIO = Manager(ADDRESS, requesthandler)

def shutdown():
    global serverIO
    serverIO.shutdown()
