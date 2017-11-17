from socket import *
import threading
import sys
import os
if os.name == 'nt':
    import win32com.client as wincl
    import pythoncom
"""This file is for the in-game text chat"""
"""This is a completely new program; thus, it must re-establish a new connection on a new port. It receives 
nickname and IP to connect to from the main script. (Therefore it can be run from terminal with arguments)"""


class ClientThread(threading.Thread):  # Run a thread continually accepting messages
    def __init__(self,socket):
        threading.Thread.__init__(self)
        self.socket = socket
        self.tts = False

    def run(self):  # Main loop
        if os.name == 'nt':  # If Windows, "coinitialize" the voice API (just something that has to be done for threads)
            pythoncom.CoInitialize()
            engine = wincl.Dispatch("SAPI.SpVoice")

        while 1:
            try:
                data = self.socket.recv(1024).decode('utf-8')  # Attempt to continually receive messages
            except:  # If connection closed, host has disconnected.
                print("Host has been disconnected.")
                return

            if data == 'tts_all':  # Set speech on if requested by host
                self.tts = True

            else:
                chatdata.append(data)  # Append message to stored data
                if len(chatdata) > 50:
                    chatdata.remove(chatdata[0])  # Saved message data can only be 50 messages max
                print(data)

                if self.tts == True:  # If Windows, use Speak; if Mac, use Say
                    if os.name == 'nt':
                        engine.Speak(str(data))  # We don't need to worry about Linux here because Linux won't be using
                    else:                        # the chat
                        os.system('say '+str(data))


def client(IP, name):  # Start a connection to the host and allow for input to be sent
    serverPort = 15000
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((IP, serverPort))
    t2 = ClientThread(clientSocket)  # Start thread
    t2.start()

    print("Connected to chat! Your name: "+name)  # Send name to host
    clientSocket.sendall(name.encode('utf-8'))

    while True:
        data = input()  # After sending message, clear screen and print out saved messages
        print('\n'*100) # This allows for nice formatting in the command prompt and for error-correction

        for i in chatdata:
            print(i)
        if data == "tts_off":  # Turn tts on or off
            t2.tts = False
        elif data == "tts_on":
            t2.tts = True
        else:
            clientSocket.send(data.encode('utf-8'))


chatdata = []
client(sys.argv[1], sys.argv[2])  # Accept arguments from the command line
