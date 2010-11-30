import xmlrpclib
import subprocess
from time import sleep
import time
import os
from SimpleXMLRPCServer import SimpleXMLRPCServer
import select
import socket

PDEB = False

class ReduceCommands(object):
    prsready = False
    reduceServer = None
    
    def __init__(self, reduceServer):
        self.reduceServer = reduceServer
    def get_version(self):
        return [("ReduceXMLRPS", "0.1")]

    def prsReady(self):
        self.prsready = True
        reduceServer.prsready = True
            
reduceServer = None

class ReduceServer(object):
    xmlrpcthread = None
    listenport = 53531    
    reducecmds = None
    finished = False
    prsready = False
    def __init__(self):
        global reduceServer
        from threading import Thread
        self.xmlrpcthread = Thread(None, self.startListening, "reducexmlrpc")
        self.xmlrpcthread.start() 
        reduceServer = self
        
    def startListening(self):
        findingport = True
        while(findingport):
            try:
                # print "p44: startListening on ", self.listenport, self.xmlrpcthread
                server = SimpleXMLRPCServer(("localhost", self.listenport), allow_none=True, logRequests=False)
                findingport = False
                # print "p47: Reduce xmlrpc listening on port %d..." % self.listenport
            except socket.error:
                self.listenport += 1
                
        self.reducecmds = ReduceCommands(self)
        server.register_instance(self.reducecmds)
        
        try:
            # print 'p55: started reduce xmlrpc server thread...'
            #server.serve_forever()
            while True:
                r,w,x = select.select([server.socket], [],[],.5)
                if r:
                    server.handle_request()
                # print "prsw: ",webserverdone
                #print "P62:", str(id(self)), repr(self.finished), str(id(reduceServer)), repr(reduceServer.finished)
                if self.finished == True:
                    # print "P63: shutting down reduce xmlrpc thread"
                    break
        except KeyboardInterrupt:
            print '^C received, shutting down server'
            server.socket.close()

def startADCC():
    prsout = open("adcc-reducelog-%d-%s" % (
                                                        os.getpid(),
                                                        str(time.time())
                                                       )
                                                        , "w")
    prsargs = ["adcc.py",
                "--invoked",
                #"--reduce-port", "%d" % reduceServer.listenport,
                "--reduce-pid", "%d" % os.getpid(),
                ]

    pid = subprocess.Popen( prsargs, 
                            stdout = prsout, 
                            stderr = subprocess.STDOUT #prserr,
                            ).pid

    return pid
                                        
class PRSProxy(object):
    # the xmlrpc interface is saved
    _class_prs = None
    prs = None
    found = False
    version = None
    finished = False
    registered = False
    
    prsport = 53530
    reducecmds = None
    xmlrpcthread = None
    reduceServer = None
            
    def __init__(self, reduceServer = None):
        try:
            self.prs = xmlrpclib.ServerProxy("http://localhost:%d" % self.prsport, allow_none=True)
            self.reduceServer = reduceServer
            PRSProxy._class_prs = self # .prs
            self.found = True
        except socket.error:
            self.found = False
            raise "NOPE"
        
    @classmethod
    def getADCC(cls, reduceServer = None):
        if  type(cls._class_prs) != type(None):
            proxy = cls._class_prs
            start = False
            return cls._class_prs
                    
        newProxy = None

        found = False
        newProxy = PRSProxy(reduceServer = reduceServer)
                
        while(not found):
            try:
                newProxy.version = newProxy.get_version()
                found = True

                if (PDEB):
                    print "P102: newProxy id", id(newProxy), newProxy.found
                    print "P100: checking for proxy up"

                # After this version call, we know it's up, we keep this
                # proxy, and start listening for commands
                if PDEB:
                    print "P109: setting found equal true"
                newProxy.found = True
                if PDEB:
                    print "P111: about to register"
                if reduceServer:
                    details =  {"port":reduceServer.listenport}
                else:
                    details = {}
                newProxy.prs.register(os.getpid(), details)
                if PDEB:
                    print "P120: Proxy found"
            except socket.error:
                newProxy.found = False
                print ("Waiting for ADCC...")
                sleep(.1)
                # try again


        return newProxy

    @classmethod
    def OLDgetPRSProxy(cls, start = False, proxy = None, reduceServer = None):
        if  type(cls._class_prs) != type(None):
            proxy = cls._class_prs
            start = False
            print "P101:", repr(dir(proxy)), repr(proxy), repr(reduceServer)
            return cls._class_prs
                    
        newProxy = None

        found = False
        try:
            if proxy == None:
                
                    
                newProxy = PRSProxy(reduceServer = reduceServer)
                newProxy.version = newProxy.get_version()
            
                if (PDEB):
                    print "P102: newProxy id", id(newProxy), newProxy.found
                    print "P100: checking for proxy up"
            else:
                if reduceServer:
                    proxy.reduceServer = reduceServer
                
                newProxy = proxy
                newProxy.version = newProxy.get_version()
                
            # After this version call, we know it's up, we keep this
            # proxy, and start listening for commands
            if PDEB:
                print "P109: setting found equal true"
            newProxy.found = True
            if PDEB:
                print "P111: about to register"
            if reduceServer:
                details =  {"port":reduceServer.listenport}
            else:
                details = {}
            newProxy.prs.register(os.getpid(), details)
            if PDEB:
                print "P120: Proxy found"
        except socket.error:
            newProxy.found = False
            if PDEB:
                print "P123: Proxy Not Found"
            # not running, try starting one...
            if start == False:
                raise
            if start:
                import time
                if (PDEB):
                    print "P132: newProxy id", id(newProxy)
                    print "P125: starting adcc.py"
                prsout = open("adcc-reducelog-%d-%s" % (
                                                        os.getpid(),
                                                        str(time.time())
                                                       )
                                                        , "w")
                prsargs = ["adcc.py",
                                        "--invoked",
                                        #"--reduce-port", "%d" % reduceServer.listenport,
                                        "--reduce-pid", "%d" % os.getpid(),
                                        
                                        ]
                
                pid = subprocess.Popen( prsargs, 
                                        stdout = prsout, 
                                        stderr = subprocess.STDOUT #prserr,
                                        ).pid
                                        
                                    
                if (PDEB):
                    print "P147: pid =", pid
                notfound = True
                if (PDEB):
                    print "P150: waiting"
                # After this version call, we know it's up, we keep this
                # proxy, and start listening for commands
                if reduceServer:
                    # if there was a reduceServer then wait to hear a response
                    while reduceServer.prsready == False:
                        if (PDEB):
                            print "P155: sleeping .1"
                        sleep(.1)

                newProxy = cls.getPRSProxy(start=False, proxy = newProxy, reduceServer = reduceServer)
                if (PDEB):
                    print "P160:", type(newProxy.found)
                    print "P161:", newProxy.version, newProxy.finished, newProxy.reduceServer
                
                if newProxy.found:
                    notfound = False
                    return newProxy
            else:
                newProxy.found = False
                

        return newProxy
        
    def unregister(self):
        if self.registered:
            import traceback
            traceback.print_stack()
            self.prs.unregister(os.getpid())
            self.registered=False
        else:
            print "WARNING: call to unregister from adcc while not registered"
            
    def register(self):
        self.prs.register(os.getpid())
        self.registered = True
        
    def __del__(self):
        # raise " no "
        print "P262: deleting proxy\n"*20
        import traceback
        if (PDEB):
            print "P153: self.found =",self.found, id(self)
        if hasattr(self.prs,"found"):
            if (PDEB):
                print "about to unregister from found prs"
            self.prs.unregister(os.getpid())
            if (PDEB):
                print "unregistered from the prs"
        
            
    def calibrationSearch(self, calRq):
        if self.found == False:
            return None
        else:
            calrqdict = calRq.asDict()
            if (PDEB):
                print "P165:", repr(calrqdict)
            cal = self.prs.calibrationSearch(calrqdict)
            if (PDEB):
                print "P167:", cal
            return cal
    def get_version(self):
        self.version = self.prs.get_version()
        return self.version
        
    def displayRequest(self, rq):
        self.prs.displayRequest(rq)
        return 
            

