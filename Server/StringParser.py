import re

class StringParser(object):
    #a class for parsing space-separated Strings 
    def __init__(self, command):
        self.commandlist = self.fullcommandlist = re.compile('[\n\r ]+').split(command)

    def __getitem__(self, key):
        return self.fullcommandlist[key]

    def 