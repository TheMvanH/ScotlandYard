##parse_map

import json
import re
import cPickle
import zlib
import base64

JSON='json'
PICKLE='pickle'
CONNECTIONS='connections'
GZIP='gzip'
PRETTY='prettyprint'
POINTS='points' #formats and modes definition
ENCODE='base64'

class map(dict):

    """this object represents a map according to the points format of ScotlandYard
    it can load maps, convert, save them, to file, and to strings.
    it takes three possible arguments at initialisation, which it uses to determine what methods to call to handle supplied data. however you can also just initialize it and use the supplied methods to handle your data.
    possible initialization argumets:
        filename: if set, this file will be loaded. datatype is looked up from the extension (.json/.pickle)
        string: if this is set, this string will be loaded
        format: use this to identify how the data should be handled. possilities are:
            CONNECTIONS: intepret the file like the old connection format.
            POINTS: intepret the file in the points format (default)
            PRETTY: when outputting as json, make the file human-readable. write-only
            GZIP: this file is gzip compressed
            ENCODE: base64 encoding is applied
            JSON: this is a json format
            PICKLE: this is a pickle format
            these can be chained by using the + operator between them
        
    saving can be done using the supplied self.save method, taking as input
        filename: if omitted, output a string. else, write to this file
        format: same as specified above, usable:
            JSON
            PICKLE
            GZIP
            PRETTY
            ENCODE
        
    save and __init__ both wrap around a list of methods for processing the data
    
    load_pickle_file(filename, format)
    load_json_file(filename, format)
    load_pickle_data(string, format)
    load_json_data(string, format)
    save_pickle_file(filename, format)
    save_json_file(filename, format)
    return_pickle_data(format)
    return_json_data(format)
    
    also provided are
    
    parse_connections(self, data)
    which will return the points data format equivalent to the input connections data
    
    This object can be accessed as a read-only dictionary exposing the contents of the last loaded map 
    
    It is dependent on python_parser for converting json objects to proper python dicts
    
    format info:
    points = 
    {
        int* : {
            taxi  : [int*],
            bus   : [int*],
            metro : [int*],
            black : [int*]
        }
    }
    connections = 
    {
        taxi: [
            [int int]*
        ]
        bus: [
            [int int]*
        ]
        metro [
            [int int]*
        ]
        black: [
            [int int]*
        ]
    }
    
    note: while it derives from object, it does not support all operations. it is read only.
    """
    
    def __init__(self,filename=None,string=None,format=''):
        self.map = {}
        mode = None
        if PICKLE in format and JSON in format:
            raise Exception('conflicting formats')
        elif PICKLE in format:
            mode = PICKLE
        elif JSON in format:
            mode = JSON
            
        if filename and string:
            raise Exception('supply a filename or a string, not both')
        if filename:
            if mode == PICKLE or (filename.endswith('.pickle') and not mode):
                self.load_pickle_file(filename, format)
            elif mode == JSON or (filename.endswith('.json') and not mode):
                self.load_json_file(filename, format)
            else:
                raise Exception('Not sure how to parse file')
        elif string:
            if mode==PICKLE:
                self.load_pickle_data(string, format)
            elif mode==JSON:
                self.load_json_data(filename, format)
            else:
                raise Exception('Not sure how to parse string')
                
    def save(self,filename=None,format=''):
        mode = None
        if PICKLE in format and JSON in format:
            raise Exception('conflicting formats')
        elif PICKLE in format:
            mode = PICKLE
        elif JSON in format:
            mode = JSON
            
        if filename:
            if mode==PICKLE or (filename.endswith('.pickle') and not mode):
                self.save_pickle_file(filename, format)
            if mode==JSON or (filename.endswith('.json') and not mode):
                self.save_json_file(filename, format)
            else:
                raise Exception('Not sure how to parse file')
        else:
            if mode==PICKLE:
                return self.return_pickle_data(format)
            elif mode==JSON:
                return self.return_json_data(format)
            else:
                raise Exception('Not sure how to parse file')
                
    def flush(self):
        self.map={}
            
    #loading functions
    
    def load_json_file(self, filename, format=''):
        f = open(filename,'rb')
        data = f.read()
        f.close()
        self.load_json_data(data, format)
        
    def load_json_data(self, data, format=''):
        if ENCODE in format:
            data = base64.b64decode(data)
        if GZIP in format:
            data = zlib.decompress(data)
        jsondata = json.loads(data)
        map = python_parser().parse(jsondata)
        if CONNECTIONS in format:
            self.map = self.parse_connections(map)
        else:
            self.map = map
    
    def load_pickle_file(self, filename, format=''):
        f = open(filename,'rb')
        data = f.write()
        f.close()
        self.load_pickle_data(data, format)
        
    def load_pickle_data(self, data, format=''):
        if ENCODE in format:
            data = base64.b64decode(data)
        if GZIP in format:
            data = zlib.decompress(data)
        self.map = cPickle.loads(data)
        
    #saving functions
            
    def save_json_file(self, filename, format=''):
        f = open(filename,'wb')
        f.write(self.return_json_data(format))
        f.close()
        
    def return_json_data(self, format=''):
        if CONNECTIONS in format:
            map = self.reverse_parse_connections(self.map)
        else:
            map = self.map
        if PRETTY in format:
            data = json.dumps(map, indent=4, separators=(', ', ': '))
        else:
            data = json.dumps(map, separators=(',', ':'))
        if GZIP in format:
            data = zlib.compress(data)
        if ENCODE in format:
            data = base64.b64encode(data)
        return data
        
    def save_pickle_file(self, filename, format=''):
        f = open(filename,'wb')
        f.write(return_pickle_data(format),f)
        f.close()
        
    def return_pickle_data(self, format=''):
        if CONNECTIONS in format:
            map = self.reverse_parse_connections(self.map)
        else:
            map = self.map
        data = cPickle.dumps(map)
        if GZIP in format:
            data = zlib.compress(data)
        if ENCODE in format:
            data = base64.b64encode(data)
        return data
        
    #parsing functions
    
    def parse_connections(self, map):
        original = map['connections']
        connections = original['taxi']+original['metro']+original['bus']+original['black']
        points = {}
        for connection in connections:
            points[connection[0]] = {'taxi':[],'bus':[],'metro':[],'black':[]}
            points[connection[1]] = {'taxi':[],'bus':[],'metro':[],'black':[]}
        for typecon in ['taxi','bus','metro','black']:
            for connection in original[typecon]:
                points[connection[0]][typecon].append(connection[1])
                points[connection[1]][typecon].append(connection[0])
        return points
        
    def reverse_parse_connections(self, map):
        connections={'taxi':[],'bus':[],'metro':[],'black':[]}
        for point in map:
            for typecon in ['taxi','bus','metro','black']:
                for connection in map[point][typecon]:
                    posone = [str(connection), str(point)]
                    postwo = [str(point), str(connection)]
                    if not ((posone in connections[typecon]) or (postwo in connections[typecon])):
                        connections[typecon].append(postwo)
        return {'connections': connections}
                        
        
    #pseudodict implementation details
    
    def __hash__(self):
        return hasher(self)
    def __getitem__(self, name):
        return self.map[name]
    def __len__(self):
        return len(self.map)
    def __contains__(self, item):
        return item in self.map
    def __iter__(self):
        return self.map.__iter__()
    def items(self):
        return self.map.items()
    def keys(self):
        return self.map.keys()
    def values(self):
        return self.map.values()
        
class simple_parser(dict):
    def __init__(self, data, format=''):
        self.map = {}
        mode = None
        if PICKLE in format and JSON in format:
            raise Exception('conflicting formats')
        elif PICKLE in format:
            mode = PICKLE
        elif JSON in format:
            mode = JSON
            
        if isinstance(data, dict):
            self.map = data
        elif mode==JSON or (not mode and data.startswith('{')):
            self.load_json_data(data, format)
        elif mode==PICKLE:
            self.load_pickle_data(data, format)
        else:
            raise Exception('Not sure how to parse file')
    def save(self, format):
        if JSON in format and PICKLE in format:
            Exception('conflicting formats')
        elif JSON in format:
            return return_json_strring(format)
        elif PICKLE in format:
            return return_pickle_string(format)
        else:
            raise Exception('Not sure how to parse file')
    def flush(self):
        self.map={}
    def dict(self):
        return self.map
    def load_json_data(self, data, format):
        if ENCODE in format:
            data = base64.b64decode(data)
        if GZIP in format:
            data = zlib.decompress(data)
        self.map = python_parser().parse(json.loads(data))
    def load_pickle_data(self, data, format):
        if ENCODE in format:
            data = base64.b64decode(data)
        if GZIP in format:
            data = zlib.decompress(data)
        self.map = cPickle.loads(data)
    def return_json_string(self, format):
        if PRETTY in format:
            data = json.dumps(self.map, indent=4, separators=(', ', ': '))
        else:
            data = json.dumps(self.map, separators=(',', ':'))
        if GZIP in format: 
            data = zlib.compress(data)
        if ENCODE in format:
            data = base64.b64encode(data)
        return data
    def return_pickle_string(self, format):
        data = cPickle.dumps(self.map)
        if GZIP in format:
            return zlib.compress(data)
        if ENCODE in format:
            data = base64.b64encode(data)
        return data
            
    def __hash__(self):
        return hasher(self)    
    def __getitem__(self, name):
        return self.map[name]
    def __len__(self):
        return len(self.map)
    def __contains__(self, item):
        return item in self.map
    def __iter__(self):
        return self.map.__iter__()
    def items(self):
        return self.map.items()
    def keys(self):
        return self.map.keys()
    def values(self):
        return self.map.values()
        
def parse_json(data):
    """a wrapper around python_parser"""
    return python_parser().parse(json.loads(data))

class python_parser(object):    
    """a simple object for parsing parsed json into proper python dicts, where all strings are checked if they represent an integer"""
    def parse(self, string):
        return self.choose_parser(string)
        
    def parse_list(self, list):
        return [self.choose_parser(item) for item in list]
        
    def parse_string(self, string):
        return int(string) if re.search('^[0-9]+$',string) else str(string)
        
    def parse_dict(self, dictionary):
        result = {}
        for item in dictionary:
            result[self.parse_string(item)]=self.choose_parser(dictionary[item])
        return result

    def choose_parser(self, something):
        return (self.parse_dict(something) if isinstance(something,dict) else
                self.parse_list(something) if isinstance(something,list) else
                self.parse_string(something) if isinstance(something,unicode) or isinstance(something,str) else
                something)
                
def hasher(mapdata):
    """
    Makes a hash from a dictionary, list, tuple or set to any level, that contains
    only other hashable types (including any lists, tuples, sets, and
    dictionaries).
    """

    if isinstance(mapdata, set) or isinstance(mapdata, tuple) or isinstance(mapdata, list):
        return tuple([hasher(e) for e in mapdata])    
    elif not isinstance(mapdata, dict):
        return hash(mapdata)
    else:
        mapcopy = {}
        for k, v in mapdata.items():
            mapcopy[k] = hasher(v) #replace the dict values with their hashes
        return hash(tuple(frozenset(mapcopy.items()))) #convert everything to tuples and hash