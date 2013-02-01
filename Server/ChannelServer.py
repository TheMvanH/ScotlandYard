#Channel server
from Networking import AsyncTCPServer
from Game import jsonlib
import config
import hashlib
import re
import os.path
import sqlite3

class ComManager(AsyncTCPServer.Manager):
    """subclass AsyncTCPServer to hook into the server object"""
    def __init__(self, ADDRESS, requesthandler, upper):
        self.upper = upper
        AsyncTCPServer.Manager.__init__(self, ADDRESS, requesthandler)

    def on_recv(self, ident, message):
        self.upper.on_recv(ident, message)
    def on_join(self, ident, client_address):
        self.upper.on_join(ident, client_address)
    def on_leave(self, ident):
        self.upper.on_leave(ident)
    def allow_connect(self, client_address):
        return self.upper.allow_connect(client_address)

class ChannelServer(object):
    """TODO: server logic, short description of everything goes here.
    there should be a list of users and a list of games. the underlying id's should be abstracted to user objects immediately
    the user objects should be initiated by on_join, and a database should be kept to be able to recall the state of all. 
    """
    def __init__(self):
        self.Database = Database(config.database)
        self.activeuserlist = []
        self.activegamelist = []
        self.backend = ComManager(
            [(config.host, config.server_port),(config.host, config.websocket_port)], 
            [AsyncTCPServer.RequestHandler, AsyncTCPServer.WebSocket], self)
        self.split = re.compile('[\n\r ]+(?!$)').split
        self.format = jsonlib.JSON+jsonlib.ENCODE
    def command_parser(self, user, command):
        """this function is responsible for the parsing of all commands which are sent to the server"""
        command = command.strip()
        try:
            commandpart = self.split(command) #split command for analysis, see specs.txt for overview
            if len(commandpart) == 0:
                raise Exception('error in command parsing: empty command')

            if   commandpart[0] == 'USER':
                ###########################################################
                ############ USER commands
                ###########################################################
                if   commandpart[1] == 'NAME':
                    if len(commandpart) != 3: raise Exception('username should be one word, without spaces')
                    user.set_username(commandpart[2])
                    self.send(user, 'USER MESSAGE Username set to ' + commandpart[2])

                elif commandpart[1] == 'PASS':
                    if len(commandpart) != 3: raise Exception('password should be one word, without spaces')
                    user.identify(commandpart[2])
                    self.send(user, 'USER MESSAGE Identified for '+ user.username)
                    
                elif commandpart[1] == 'SETPASS':
                    if len(commandpart) != 3: raise Exception('password should be one word, without spaces')
                    user.set_password(commandpart[2])
                    self.send(user, 'USER MESSAGE Set password for '+user.username)
                    
                elif commandpart[1] == 'MODE':
                    raise Exception('NOT IMPLEMENTED ERROR') #TODO: implement

                elif commandpart[1] == 'INFO':
                    if len(commandpart) > 3: raise Exception('too much arguments')
                    if len(commandpart) == 2: testuser = user
                    else:                     testuser = self.get_user_by_name(commandpart[2], True)
                    info = testuser.info()
                    infostr = jsonlib.simple_parser(info).save(self.format)
                    self.send(user, 'USER INFO '+infostr)

                elif commandpart[1] == 'ADMIN':
                    if len(commandpart) != 3: raise Exception('password should be one word, without spaces')
                    user.admin(commandpart[2])
                    self.send(user, 'USER MESSAGE admin identified')
                    
                else: raise Exception('Unknown command, USER supports NAME, PASS, SETPASS, MODE, INFO and ADMIN')

            elif commandpart[0] == 'GAME':
                ###########################################################
                ############ GAME commands
                ###########################################################
                if len(commandpart) <= 2: raise Exception('no command or channel name entered')

                elif commandpart[2] == 'JOIN':
                    if len(commandpart) != 3: raise Exception('missing channel name or misformatted command')
                    if self.exist_game(commandpart[1]):game = self.get_game_by_name(commandpart[1]):
                    else: game = Game(commandpart[1], self, user)
                    game.join(user)

                else:
                    if not self.exist_game(commandpart[1]): raise Exception('game does not exist')
                    game = self.get_get_game_by_name(commandpart[1])

                    if   commandpart[2] == 'DESTROY':
                        if len(commandpart) != 3: raise Exception('misformatted command')
                        if game.shutdown(user): 
                            self.activegamelist.remove(game)
                            del game
                        else: raise Exception('you don\t have permission to shut down the game')

                    elif commandpart[2] == 'RESET':
                        if not game.reset(user): raise Exception('you don\'t have permission to reset the game')







                else: raise Exception('NOT IMPLEMENTED ERROR') #TODO: implement
            elif commandpart[0] == 'ADMIN':
                ###########################################################
                ############ ADMIN commands
                ###########################################################
                if   not 'a' in user.modes: raise Exception('You don\' have admin status')

                elif commandpart[1] == 'KILL':
                    if len(commandpart) != 3: raise Exception('KILL takes one command')
                    target = self.get_user_by_name(commandpart[2])
                    self.backend.kick(target.ident)
                        
                elif commandpart[1] == 'BAN':
                    if   commandpart[2] == 'IP':
                        if not (len(commandpart) == 4 and re.search('^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$',commandpart[3])): raise Exception('Malformatted IP')
                        self.Database.addban(commandpart[3])
                            
                    elif commandpart[2] == 'USER':
                        if len(commandpart) != 4: raise Exception('Malformatted username')
                        user = self.get_user_by_name(commandpart[3], True)
                        self.Database.addban(user.ip)

                    else: raise Exception('ADMIN BAN takes either USER or IP as subcommand')

                elif commandpart[1] == 'UNBAN':
                    if   commandpart[2] == 'IP':
                        if not(len(commandpart) == 4 and re.search('^[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}$',commandpart[3])): raise Exception('Malformatted IP')
                        self.Database.removeban(commandpart[3])

                    elif commandpart[2] == 'USER':
                        if len(commandpart) != 4: raise Exception('Malformatted username')
                        user = self.get_user_by_name(commandpart[3])
                        self.Database.removeban(user.ip)
                            
                    else: raise Exception('ADMIN UNBAN takes either USER or IP as subcommand')

                elif commandpart[1] == 'WIPE':
                    if len(commandpart) != 3: raise Exception('malformatted request')
                    self.Database.wipe(commandpart[2])
                        
                elif commandpart[1] == 'DESTROY':
                    raise Exception('NOT IMPLEMENTED ERROR')

                elif commandpart[1] == 'EXECUTE':
                    if len(commandpart) <= 2: raise Exception('missing argument')
                    commandcode = ' '.join(commandpart[2:])
                    err = res = None
                    try:
                        exec commandcode
                    except SyntaxError:
                        try:
                            res = eval(commandcode)
                        except Exception as e:
                            err = str(e)
                    except Exception as e:
                        err = str(e)
                    if res:
                        self.send(user, 'USER RESULT '+res)
                    elif err:
                        self.send(user, 'USER ERROR '+err)
                    else:
                        self.send(user, 'USER RESULT SUCCESSFUL')
                        
                elif commandpart[1] == 'BROADCAST':
                    if len(commandpart) != 3: raise Exception('malformatted request')
                    self.backend.sendall('USER MESSAGE ' + commandpart[2])

                else: raise Exception('Unknown command, ADMIN supports KILL, BAN, UNBAN, WIPE, DESTROY, EXECUTE and BROADCAST')

            elif commandpart[0] == 'QUERY':
                ###########################################################
                ############ QUERY command
                ###########################################################
                if len(commandpart) <= 2: raise Exception('no message detected')
                receiver = self.get_user_by_name(commandpart[1])
                message  = re.search('QUERY[\r\n ]+[^\r\n ]+[\r\n ]+(.*)', command, re.DOTALL).group(1)
                self.send(self.get_user_by_name(commandpart[1]), 'QUERY ' + user.username +' '+message)
                    
            elif commandpart[0] == 'PONG':
                ###########################################################
                ############ PONG command
                ###########################################################
                raise Exception('NOT IMPLEMENTED ERROR') #TODO: implement, shoud reset last response timer

            else: raise Exception('Command not recognized')
                #catchall
                
        except Exception as error:
            self.send(user, 'ERROR '+ str(error)) #an exception was thrown somewhere


    #backend code
    def on_recv(self, ident, message):
        self.command_parser(self.get_user_by_ident(ident), message)
    def on_join(self, ident, client_address):
        user = User(ident, client_address, self.Database)
        self.activeuserlist.append(user)
    def on_leave(self, ident):
        user = self.get_user_by_ident(ident)
        user.save()
        self.activeuserlist.remove(user)
        del user
    def allow_connect(self, client_address):
        return not (client_address[0] in self.Database.ip_bans())
    def kick(self, user):
        self.backend.kick(user.ident)
    def send(self, user, message):
        self.backend.send(user.ident, message)
    def sendall(self, message):
        self.backend.send(message)
    def shutdown(self):
        #graceful shutdown
        try: self.backend.shutdown()
        except: pass
        try: self.Database.shutdown()
        except: pass
        del self.backend
        del self.Database

    #utility code
    def get_game_by_name(self, channel):
        for game in self.activegamelist:
            if game.name == channel:
                return game
        raise Exception('game not found')

    def exist_game(self, channel):
        return channel in [game.name for game in self.activegamelist]

    def get_user_by_name(self, username, offline=False):
        for user in self.activeuserlist:
            if user.username == username:
                return user
        #not in the active list and offline user selection is allowed
        if offline and username in self.Database.accounts():
            return TempUser(username, self.Database)
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
        if self.username in self.Database.accounts():
            raise Exception('This username is already registered')
        else:
            self.password = hashlib.md5(passhash).hexdigest() #hash password.
            self.Database.addaccount(self.username, self.password, self.ip)
            self.modes += 'i'
    def identify(self, passhash):
        if 'i' in self.modes:
            raise Exception('this username is already identified')
        password = hashlib.md5(passhash).hexdigest()
        if self.Database.verify(self.username,password):
            self.password = password
            self.Database.updateip(self.username, self.ip)
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

class TempUser(User):
    #user-like object spawned when the user isn't online but things are done
    def __init__(self, username, database):
        self.username = username
        self.Database = database
        self.password, self.ip = self.Database.getinfo(self.username)
        self.modes = ''
        self.games = []
        self.ident = None



class Database(object):
    """wrapper around database"""
    #TODO: implement database
    #tables:
    #   users:
    #       username
    #       password
    #       ip
    #   ipbans:
    #       ip
    #   server     misc server storage
    #       key
    #       value
    def __init__(self, filename):
        filename = config.database
        if not os.path.isfile(filename):
            db = sqlite3.connect(filename)
            c = db.cursor()
            c.execute("CREATE TABLE users (username, password, ip)")
            c.execute("CREATE TABLE ipbans (ip)")
            c.execute("CREATE TABLE server (key, value)")
            c.execute("INSERT INTO server VALUES (?,?)",("adminpassword",hashlib.md5(config.adminpass).hexdigest()))
            db.commit()
            db.close()
        self.db = sqlite3.connect(filename, check_same_thread=False)
        self.db.text_factory = str
        self.cursor = self.db.cursor()
    def ip_bans(self):
        return [i[0] for i in self.cursor.execute('SELECT * FROM ipbans')]
    def addban(self, ip):
        self.cursor.execute("INSERT INTO ipbans VALUES (?)",(ip,))
    def removeban(self, ip):
        self.cursor.execute("DELETE FROM ipbans WHERE ip=?",(ip,))
    def accounts(self):
        return [i[0] for i in self.cursor.execute('SELECT username FROM users')] #list of usernames
    def addaccount(self, username, password, ip):
        self.cursor.execute("INSERT INTO users VALUES (?,?,?)",(username, password, ip))
    def updateip(self, username, ip):
        self.cursor.execute("UPDATE users SET ip=? WHERE username=?",(ip, username))
    def wipe(self, username):
        self.cursor.execute("DELETE FROM users WHERE username=?",(username,))
    def getinfo(self, username):
        return self.cursor.execute("SELECT password, ip FROM users WHERE username=?",(username,)).fetchone()
    def verify(self, username, password):
        return (username, password) in [i for i in self.cursor.execute('SELECT username, password FROM users')] 
    def checkadminpass(self, adminpass):
        return hashlib.md5(adminpass).hexdigest() == self.cursor.execute('SELECT value FROM server WHERE key="adminpassword"').fetchone()[0]
    def setadminpass(self, adminpass):
        self.cursor.execute('UPDATE server SET value=? WHERE key="adminpassword"',(hashlib.md5(adminpass).hexdigest(),))

    def shutdown(self):
        self.db.commit()
        self.db.close()
