#chatclient
import AsyncTCPClient

class Manager(AsyncTCPClient.Manager):
    def on_recv(self, msg):
        print msg
        if msg == 'PING!':
            self.send('PONG!')
        elif msg == 'PONG!':
            self.send('PING!')

def run(ADDRESS=('192.168.2.15',9999)):
    clientIO = Manager(ADDRESS)
    while True:
        comm = raw_input()
        if comm == '/quit':
            break
        elif comm == '/disc':
            clientIO.disconnect()
        elif comm == '/reco':
            clientIO.reconnect()
        else:
            connected = clientIO.send(comm)
            if not connected:
                break
    clientIO.shutdown()