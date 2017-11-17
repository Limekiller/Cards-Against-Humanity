from socket import *
import os
import threading
import select
import sys
if os.name == 'nt':
    import win32com.client as wincl
    import pythoncom
"""This file is for the in-game text chat server"""
"""This is a completely new program; thus, it must re-establish a new connection on a new port. It receives 
nickname from the main script. (Therefore it can be run from terminal with arguments)"""

class searchthread(threading.Thread):
    """Connection search thread to find connections while also accepting keyboard input """

    def __init__(self,serversocket):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.quitting = False
        self.serversocket = serversocket

    def shutdown(self):  # For closing thread
        if self.quitting:
            return
        self.quitting = True
        self.join()

    def run(self):  # Main loop
        color = 0
        while not self.quitting:
            rr,rw,err = select.select([self.serversocket],[],[],1)  # Wait for open socket
            if rr:
                connectionSocket, addr = self.serversocket.accept()  # Create connection
                newthread = ServerThread(connectionSocket, addr)  # Store connection as thread
                newthread.start()  # Start thread
                threads[str(addr[0])] = newthread  # Keep track of thread in dictionary


class ServerThread(threading.Thread):
    """Main client thread for connections"""
    def __init__(self,consock,addr):
        threading.Thread.__init__(self)
        self.consock = consock
        self.addr = addr
        self.tts = False
        self.name = None

    def run(self):  # Main loop
        if os.name == 'nt':  # Coinitialize speech engine if Windows
            pythoncom.CoInitialize()
            engine = wincl.Dispatch("SAPI.SpVoice")

        while 1:
            try:
                data = self.consock.recv(1024).decode('utf-8')  # Continually receive data
                if sender[0] != self.name:  # If different sender than previous message, save new sender
                    sender[0] = self.name   # and generate, send dividing bar to all clients
                    bar = '\n-----------------------------------------------------------------------'
                    #bar = '\n'+self.name+' '               # This code allows the sender's name to be prepended to the
                    #for i in range(70 - len(self.name)):   # dividing bar as a sort of 'section header'
                    #    bar += '-'                         # Kind of annoying (esp. with tts) so I turned it off
                    cdata(bar)
                    print(bar)  # Add bar to saved message data, print and send to all clients
                    send_to_all(bar, '')
            except:  # If a connection has been forcibly closed between a specific client, tell all clients
                print(self.name+" has disconnected.")   # who has disconnected
                threads.pop(self.addr, None)  # Remove thread from dictionary
                send_to_all(self.name+" has disconnected.",self.name)
                break

            if self.name == 'None':  # Set nickname
                self.name = data
            else:
                data = str(self.name+": "+data)  # Take incoming data, prepend sender's name, and send to all clients
                cdata(data)  # Also add to saved message data
                print(data)
                send_to_all(data, '')

                if self.tts == True:  # TTS stuff
                    if os.name == 'nt':
                        engine.Speak(data)
                    else:
                        os.system('say '+str(data))

    def send(self,data):  # Method for sending data to a specific client
        self.consock.sendall(data)


def send_to_all(data, name):  # Function for easy sending to all clients, super helpful
    for i in threads.keys():
        if threads[i].name != name:
            threads[i].send(data.encode('utf-8'))


def cdata(data):  # Easy function for checking saved message data size before appending
    if len(chatdata) > 50:
        chatdata.remove(chatdata[0])
    chatdata.append(data)


def server(name):  # Main server thread
    serverPort = 15000
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serverSocket.bind(('', serverPort))
    serverSocket.listen(1)
    name = name

    t1 = searchthread(serverSocket)  # Create server listening thread
    t1.start()
    print("Connected to chat! Your name: "+name)

    while True:
        data = input()
        print('\n'*100)  # After input, send dividing bar and add to message data
        if sender[0] != name:
            sender[0] = name
            bar = '\n-----------------------------------------------------------------------'
            #bar = '\n'+name+" "
            #for i in range(70 - len(name)):
            #    bar += '-'
            cdata(bar)
            send_to_all(bar, '')
        cdata(name+': '+data)  # Prepend name to message

        for i in chatdata:  # Print all saved chat data
            print(i)
        if data == "tts_off":  # Misc tts stuff
            for i in threads.keys():
                threads[i].tts = False
        elif data == "tts_on":
            for i in threads.keys():
                threads[i].tts = True
        elif data == "tts_all":
            for i in threads.keys():
                threads[i].send(data.encode('utf-8'))
        else:
            for i in threads.keys():
                threads[i].send(str(name+": "+data).encode('utf-8'))

chatdata = []
sender = ['None']  # Create chat data list, sender item, and threads dict
threads = {}
server(sys.argv[1])



