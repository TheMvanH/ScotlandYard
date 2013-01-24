import SimpleHTTPServer
import SocketServer
import threading
PORT = 8000

Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
httpd = SocketServer.TCPServer(("localhost", PORT), Handler)

print "serving at port", PORT
#httpthread = threading.Thread(target=httpd.serve_forever, name="httpthread")
#httpthread.start()
httpd.serve_forever()