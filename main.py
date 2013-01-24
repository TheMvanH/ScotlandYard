#order of initialization
#Channelserver regulates the main part of the communications. however a part is done by the Webserver which allows access to 
#the games from a browser via websockets. websockets are regarded just like normal clients
#also a standalone webserver is required to host the main pages. The rest of the communications however is done by websockets

#import everything
import config
from Networking import *
from Game import *
from Webserver import *
from Server import *
imports = [jsonlib, config, AsyncTCPClient, AsyncTCPServer, ChannelServer]


#starts the server
Main = ChannelServer.ChannelServer()

def rel():
    global Main
    global imports
    try:
        Main.shutdown()
    except:
        pass
    #reload all the things
    [reload(i) for i in imports]
    Main = ChannelServer.ChannelServer()
