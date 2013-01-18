#Channel server
from Networking import AsyncTCPServer
from Game import jsonlib
import hashlib
import re

class ComManager(AsyncTCPServer.Manager):
	"""subclass AsyncTCPServer to hook into the server object"""
	def __init__(self, ADDRESS, upper):
		self.upper = upper
		AsyncTCPServer.__init__(self, ADDRESS)

	def on_recv(self, ident, message):
		self.upper.recv(ident, message)
	def on_join(self, ident, client_address):
		self.upper.join(ident, client_address)
	def on_leave(self, ident):
		self.upper.leave(ident)
	def allow_connect(self, ident, client_address):
		self.allow_connect(client_address)

class ChannelServer(object):
    """TODO: server logic, short description of everything goes here.
    there should be a list of users and a list of games. the underlying id's should be abstracted to user objects immediately
    the user objects should be initiated by on_join, and a database should be kept to be able to recall the state of all. 
    """
    def __init__(self, ADDRESS=('127.0.0.1',9999)):
        self.Database = Database()
        self.activeuserlist = []
        self.activegamelist = []
        self.backend = ComManager(ADDRESS, self)
        self.split = re.compile('[\n\r ]+').split
        self.format = jsonlib.JSON+jsonlib.ENCODE
    def command_parser(self, user, command):
        """this function is responsible for the parsing of all commands which are sent to the server"""
        try:
            commandpart = self.split(command) #split command for analysis, see specs.txt for overview
            if len(commandpart) == 0:
                raise Exception('error in command parsing: empty command')

            if   commandpart[0] == 'USER':
                if   commandpart[1] == 'NAME':
                    if len(commandpart) == 3:
                        user.set_username(commandpart[2])
                    else:
                        raise Exception('username should be one word, without spaces')
                elif commandpart[1] == 'PASS':
                    if len(commandpart) == 3:
                        user.identify(commandpart[2])
                    else:
                        raise Exception('password should be one word, without spaces')
                elif commandpart[1] == 'SETPASS':
                    if len(commandpart) == 3:
                        user.set_password(commandpart[2])
                    else:
                        raise Exception('password should be one word, without spaces')
                elif commandpart[1] == 'MODE':
                    raise Exception('NOT IMPLEMENTED ERROR') #TODO: implement
                elif commandpart[1] == 'INFO':
                    if len(commandpart) > 3:
                        raise Exception('too much arguments')
                    else:
                        if len(commandpart) == 2:
                            testuser = user
                        else:
                            testuser = get_user_by_name(commandpart[2])
                        info = testuser.info()
                        infostr = jsonlib.simple_parser(info).save(self.format)
                        self.send(user, 'USER INFO '+infostr)
                elif commandpart[1] == 'ADMIN':
                    if len(commandpart) == 3:
                        user.admin(commandpart[2])
                    else:
                        raise Exception('password should be one word, without spaces')
                else:
                    raise Exception('Unknown command, USER supports NAME, PASS, SETPASS, MODE, INFO and ADMIN')
            elif commandpart[0] == 'GAME':
                pass
            elif commandpart[0] == 'ADMIN':
                pass
            elif commandpart[0] == 'QUERY':
                if len(commandpart) > 2:
                    receiver = self.get_user_by_name(commandpart[1])
                    message  = re.search('QUERY[\r\n ]+[^\r\n ]+[\r\n ]+(.*)', command, re.DOTALL).group(1)
                else:
                    raise Exception('no message detected')
            elif commandpart[0] == 'PONG':
                pass
            else:
                raise Exception('Command not recognized')


    #backend code
    def on_recv(self, ident, message):
    	self.command_parser(self.get_user_by_ident(ident), message)
    def on_join(self, ident, client_address):
        user = User(ident, client_address, self.Database)
        self.activeuserlist.append(user)
    	pass
   	def on_leave(self, ident):
   		user = self.get_user_by_ident(ident)
        user.save()
        self.activeuserlist.remove(user)
        del user
   	def allow_connect(self, ident, client_address):
   		return not (client_address[0] in self.Database.ip_bans()):
    def kick(self, user):
        self.backend.kick(self, user.ident)
    def send(self, user):
        self.backend.send(self, user.ident, message)

    #utility code
    def get_user_by_name(self, username):
        for user in self.activeuserlist:
            if user.username == username:
                return user
        raise Exception('user not found')
    def get_user_by_ident(self, ident):
        for user in self.activeuserlist:
            if user.ident == ident:
                return user
        raise Exception('user not found')

        
class Game(object):
    def __init__(self):
        pass
        
class User(object):
    def __init__(self, ident, client_address, Database):
        self.modes = ''
        self.username = client_address[0]+':'+str(client_address[1])
        self.password = None
        self.ident = ident
        self.ip = client_address[0]
        self.games = []
        self.Database = Database
    def set_username(self, user):
        self.modes = self.modes.replace('i','')
        self.username = user
        for game in self.games:
            game.update_info()
    def set_password(self, passhash):
        if self.username in self.Database.accounts()
            raise Exception('This username is already registered')
        else:
            self.password = hashlib.md5(passhash).hexdigest() #hash password.
            self.modes += 'i'
    def identify(self, passhash):
        if 'i' in self.modes:
            raise Exception('this username is already identified')
        password = hashlib.md5(passhash).hexdigest()
        if self.Database.verify(self.username,password):
            self.password = password
            self.modes += 'i'
        else:
            raise Exception('Wrong password')
    def info(self):
        return {'modes':self.modes,
                'ip':self.ip,
                'games':[game.name for game in self.games],
                'id':self.ident,
                'username':self.username}
    def save(self):
        if 'i' in self.modes:
            pass #TODO: store in database
    def admin(self, adminhash):
        if 'a' in self.modes:
            raise Exception('you\'re already admin')
        elif self.Database.checkadminpass(adminhash):
            self.modes += 'a'
        else:
            raise Exception('Wrong password')

class Database(object):
    """wrapper around database"""
    #TODO: implement database
    def __init__(self):
        pass
    def ip_bans(self):
        return [] #TODO: return banned ip's
    def accounts(self):
        return [] #list of usernames
    def verify(self, username, password):
        return True #TODO: implement username password database
    def checkadminpass(self, adminpass):
        if hashlib.md5(adminpass).hexdigest() == None:
            pass
        return True #TODO: Implement in database
    def setadminpass(self, adminpass)
        pass = hashlib.md5(adminpass).hexdigest() #TODO: store in database
