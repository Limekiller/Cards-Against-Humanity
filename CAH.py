# import urllib.request
# Low-level networking tools
from socket import *
# For making the program wait for others to catch up
import time
# To run simulatneous threads
import threading
# For closing threads
import select
# For OS detection
import os
# For randomization
import random

# TODO: Improve end-of-round screen
# TODO: Allow anyone to join at any time
# TODO: Technically it should work over the internet if the host is able to port-forward!!  :)

# THE GAME WORKS
# IT FUCKING WORKS
# Notes:
# If you have ANY questions about how something works, ask me and I'll add it here.
#
# Since this script runs for both the server AND the client, if you want to make sense of it, you sort of have to bounce
# between the client's functions and the server's functions. Figure out where the clients are waiting for verification
# from the server, and where the server sends that verification. Everything lines up, and it will make a lot more sense
# once you see the bigger picture.
#
# To support multiple blanks, the .sent variable has been changed to a list. This has required a bunch of small
# changes throughout the program to support it. Right now these are mostly undocumented.
#
# .encode and .decode is used when sending data to and from a host or client. The socket library can only send the bytes
# themselves, not strings or ints or any sort of complicated object, so these objects are translated into bytes through
# 'UTF8', a character encoding for Unicode
#
# To distinguish between the data received by a client, the client attaches a tag to the end of it. For example, when
# a user sends a card to the server, it really sends xcard, where x is the card to be sent.
#
# Whenever a client needs to wait for the server before moving on in the program, I set a variable to 'F', and
# continually reset that variable to anything received from the server until that variable equals 'T'. So once the
# server is ready to move on, it sends a 'T' to every client, and they all continue together.
# There is only one place where the server has to wait for a client, so I made a global variable that gets changed in
# that client's connection thread, allowing the server to continue.
#
# Cards have to be kept track locally by the client, as well as by the server for each client. So each connection thread
# stores a self.hand variable, but there is also a hand variable that shows up in client functions.


# Create list of question cards and answer cards based on files
# If we want to, we could find a way to put this all in one file, but we already have so many...
# Then again, maybe that's *why* we should conserve space.
with open('questioncards.txt') as f:
    questions = f.read().splitlines()
with open('answercards.txt') as f:
    answers = f.read().splitlines()


# SERVER CONNECTION THREAD
class SearchThread(threading.Thread):
    """This runs on the server when you first type 'play.' It's what allows the server to establish connections
     with others. When you type 'play' the second time, it is terminated."""

    def __init__(self, serversocket, server_name):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.quitting = False
        self.server_name = server_name
        self.serversocket = serversocket

    # For closing thread
    def shutdown(self):
        if self.quitting:
            return
        self.quitting = True
        self.join()

    # Main Loop
    def run(self):
        while not self.quitting:
            # Wait for open socket
            rr, rw, err = select.select([self.serversocket], [], [], 1)

            if rr:
                # Create connection
                connection_socket, addr = self.serversocket.accept()
                connection_socket.sendall(self.server_name.encode('utf8'))

                if connection_socket.recv(1024).decode('utf8') == 'T':
                    # Store connection as thread
                    newthread = ServerThread(connection_socket, addr)
                    # Start thread
                    newthread.start()
                    # Keep track of thread in dictionary
                    threads[str(addr[0])] = newthread
                    print(str(addr[0]) + " has connected!")
                    send_to_all(str(addr[0]))


# SERVER SOCKET THREAD
# Controls all data to and from host.
class ServerThread(threading.Thread):
    """The server stores each connection in a thread that continues to run throughout the duration of the program.
    This is required for multiple connections to different clients to be maintained. Thus, when a server sends data
    to a client or receives data from a client, it goes through this thread."""

    def __init__(self, consock, addr):
        threading.Thread.__init__(self)
        # The connection socket
        self.consock = consock
        # Holds the card the player has played; also used for determining whether a card has been played or not
        self.sent = []
        # IP Address
        self.addr = addr
        # Is the user the judge for the round?
        self.judge = False
        # User's nickname
        self.name = None
        # Score, duh.
        self.score = 0
        # User's hand
        self.hand = []

    # Main loop
    def run(self):
        global host_card
        global q_card
        # Continually receive data
        while 1:
            data = self.consock.recv(1024)

            # If receiving name data, set nickname
            if self.name == 'None':
                self.name = data.decode('utf-8')

            # If receiving a card, save it in the 'sent' variable
            if data.decode('utf8')[-4:] == 'card':
                # Make sure the card is in the hand
                if data.decode('utf8')[:-4] in '01234' and self.hand[int(data.decode('utf8')[:-4])] != 'trash':
                    self.sent.append(self.hand[int(data.decode('utf8')[:-4])])
                    # Remove card from hand
                    # self.hand.remove(self.hand[int(data.decode('utf8')[:-4])])
                    self.hand[int(data.decode('utf8')[:-4])] = 'trash'
                    if len(self.sent) == find_blanks(q_card):
                        print(self.name + ' has played their card!')
                        self.consock.sendall('T'.encode('utf8'))
                        # Only notify people that have already played their cards that somebody else has played a card.
                        # Otherwise things get messed up yo
                        for i in threads.keys():
                            if threads[i].sent:
                                threads[i].send((self.name + ' has played their card!').encode('utf8'))
                    else:
                        self.consock.sendall('M'.encode('utf8'))
                # Only accept cards in the hand
                else:
                    self.consock.sendall('F'.encode('utf8'))

            # If receiving a judge's decision, make sure that the chosen card has actually been played
            if data.decode('utf8')[-5:] == 'judge':
                if (data.decode('utf8')[:-5]) in [str(i + 1) for i in range(len(randomize_cards))]:
                    # Get the actual data on the card (not just the integer value in the cards played list)
                    judge_choice = randomize_cards[int(data.decode('utf8')[:-5]) - 1]
                    # Go through every other players sent cards, and declare them the winner of it was theirs.
                    # If it is none of theirs, it must be the host's; declare the host the winner.
                    client_card = False
                    for i in threads.keys():
                        if judge_choice == threads[i].sent:
                            client_card = True
                            threads[i].score += 1
                            self.consock.sendall('T'.encode('utf8'))
                            host_card = threads[i].name
                    if not client_card:
                        self.consock.sendall('T'.encode('utf8'))
                        host_card = 'Host'
                # Only accept valid input
                else:
                    self.consock.sendall('F'.encode('utf8'))

    # Method for receiving data from a specific client. Don't remember if I actually used this.
    def recv(self, buffer):
        data = self.consock.recv(buffer).decode('utf-8')
        return data

    # Method for sending data to a specific client
    def send(self, data):
        self.consock.sendall(data)


class LANSearchThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.quitting = False
        self.server_port = 12000
        self.server_name = gethostbyname(gethostname()).split('.')

    def shutdown(self):
        if self.quitting:
            return
        self.quitting = True
        try:
            self.join()
        except:
            pass

    # Main Loop
    def run(self):
        a = int(self.server_name[2])
        b = 1
        first_check = 1
        while not self.quitting and (a < 255):
            # Wait for open socket
            # rr, rw, err = select.select([self.serversocket], [], [], 1)
            # if rr:
            if b == 255:
                if first_check == 1:
                    first_check = 0
                    a = 0
                a += 1
                b = 1
            server_port = 12000
            server_name = gethostbyname(gethostname()).split('.')

            # Starts at current subnet, and attempts to make a connection on port 12000 for every IP address.
            # Works outward from subnet, alternating up and down the list.
            # This is gross and I want to change it but I haven't thought of a better idea yet.
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.settimeout(0.000001)
            try:
                client_socket.connect(
                    (server_name[0] + '.' + server_name[1] + '.' + str(a) + '.' + str(b), server_port))
                server_id = client_socket.recv(1024).decode('utf8')
                client_socket.send('F'.encode('utf8'))
                found_game = server_name[0] + '.' + server_name[1] + '.' + str(a) + '.' + str(b)
                found_games.append(found_game)
                print(found_games.index(found_game)+1, ':\t'+found_game+', '+server_id)
            except:
                pass
            b += 1
        self.shutdown()


def search():
    print('\n' * 100)
    print("Enter 'stop' to stop searching for games. Enter the number of a game to connect to it.")
    s1 = LANSearchThread()
    s1.start()
    stop = 'f'
    while (stop != 'stop' and stop not in [str(i) for i in range(len(found_games) + 1)]) and not s1.quitting:
        stop = input("Games found:\n")
    s1.shutdown()
    if stop in [str(i) for i in range(len(found_games) + 1)]:
        return client(found_games[int(stop) - 1])


def find_blanks(stri):
    num = 0
    for i in stri:
        if i == '_':
            num += 1
    if num == 0:
        num = 1
    return num


def send_to_all(data):
    """Easily-callable function for sending data to everyone"""
    for i in threads.keys():
        threads[i].send(data.encode('utf-8'))


def server():
    """Sets up host connection and begins listening for clients"""
    print('\n'*100)
    server_name = input("Please enter a name for your server: ")

    # Set up socket and begin listening for connections
    server_port = 12000
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(('', server_port))
    server_socket.listen(1)

    print("Searching for connections...")
    print("Your IP is " + gethostbyname(gethostname()))  # Get LAN IP address
    # print("Your IP is "+urllib.request.urlopen('http://ident.me').read().decode('utf8'))
    # ^ This gets public internet IP, but it doesn't work because of NAT addressing. May be able to use a UPnP library
    # for global internet, but it will be a lot of work.

    # Create server listening thread
    t1 = SearchThread(server_socket, server_name)
    t1.start()

    # Wait for user to initiate game and shut down listening thread
    cont = "F"
    while cont != 'play':
        cont = input("Type play to begin\n")
        if cont == 'play':
            t1.shutdown()
    return play_h(threads)


def client(ip):
    """Creates a connection to the host specified"""

    # If user is a client, create socket and connection to specified IP
    server_name = ip
    server_port = 12000
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((server_name, server_port))
    time.sleep(1)
    client_socket.send('T'.encode('utf8'))

    # Wait for host to initiate game
    cont = "F".encode('UTF-8')
    while cont.decode('UTF-8') != "T":
        cont = client_socket.recv(1024)
        if cont.decode('UTF-8') != "T":
            print(cont.decode('UTF-8') + " has connected!")
            print("Waiting for host...")

    return play_c(client_socket, server_name)


def play_h(active_threads):
    """Collects names from clients, and opens chat for the server"""

    print("\n" * 100)
    names = 0
    name = input("Please enter your nickname: ")

    send_to_all("T")
    print("Waiting for players...")
    # Wait for all clients to submit nicknames
    while names < len(active_threads):
        for i in active_threads.keys():
            names += 1
            if active_threads[i].name == 'None':
                names = 0

    # Create string of names and send to all clients
    # TODO: Change this this to a stored list so we need way less string formatting
    names = "You are playing with " + str(name) + ", "
    for j in active_threads.keys():
        names += str(active_threads[j].name) + ", "

    # This is all string formatting, would be better if we just stored names in a list #####
    names = names[len(names) - 2::-1]
    for i in names:
        if i == ' ':
            names = names[:names.index(' ') + 1] + "dna" + names[names.index(' '):]
            break
    names = names[:0:-1]
    # It removes the final comma and adds an and between the last two names
    #########

    print('\n' * 100)
    print(names + '\n')
    send_to_all("T")
    send_to_all(names + '\n')

    # If Windows, open chat like this
    if os.name == 'nt':
        try:
            os.system("start cmd /c ChatServer.py " + name)
        except:
            # In case there's some problem with the chat (file doesn't exist?)
            print("Connection to chat failed.")
            pass
    # Else, try this Mac only version
    elif os.name == 'posix':
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            os.system('chmod 755 ' + dir_path + '/runInTerminal.sh')
            os.system(dir_path + '/runInTerminal.sh python3 ' + dir_path + '/ChatServer.py ' + name)
        # If Linux, sorry, no chat :(
        except:
            print("Connection to chat failed.")
    else:
        print("Connection to chat failed.")
    # Wait for a second for clients to catch up
    time.sleep(1)
    return deal_h(name)


def play_c(clientsocket, ip):
    """Sends name to host, and opens chat for client."""

    print('\n' * 100)
    name = 'None'
    # Send nickname to host
    while name == 'None':
        name = input("Please enter your nickname: ")
        clientsocket.send(name.encode('utf-8'))

    print("Connected!")
    print("Waiting for players...")
    cont = "F".encode('UTF-8')
    # Wait for host
    while cont.decode('UTF-8') != "T":
        cont = clientsocket.recv(1024)
    print('\n' * 100)
    # Print all names
    print(clientsocket.recv(1024).decode('utf-8'))

    # If Windows, open chat client like this
    if os.name == 'nt':
        try:
            os.system("start cmd /c ChatClient.py " + str(ip) + " " + name)
        except:
            # This shouldn't really happen but hey
            print("Connection to chat failed.")
            pass
    # Otherwise, assume it's a Mac
    elif os.name == 'posix':
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            os.system('chmod 755 ' + dir_path + '/runInTerminal.sh')
            os.system(dir_path + '/runInTerminal.sh python3 ' + dir_path + '/ChatClient.py ' + str(ip) + ' ' + name)
        # RIP Linux
        except:
            print("Connection to chat failed.")
    else:
        print("Connection to chat failed.")

    return deal_c(clientsocket, name)


def deal_c(clientsocket, name, hand=[]):
    """Builds a hand from cards dealt by the server"""

    # While less than 5 cards in hand, continue to receive cards
    while len(hand) < 5:
        card = clientsocket.recv(1024).decode('utf-8')
        hand.append(card)
    # Print hand
    print('\n' * 100)
    print("Your hand is:")
    for i in hand:
        print(hand.index(i) + 1, '\t' + i)
    return game_c(clientsocket, name, hand)


def deal_h(name, hand=[], score=0):
    """Function for dealing cards to all clients"""

    # For each client, send 5 cards
    for i in threads.keys():
        temp_hand = []
        for j in range(len(threads[i].hand)):
            if threads[i].hand[j] != 'trash':
                temp_hand.append(threads[i].hand[j])
        threads[i].hand = temp_hand
        # Keep track of cards dealt and choose again if card was already dealt
        while len(threads[i].hand) < 5:
            # If people play a super long game, this might take a while if
            # there's only a few cards left. Should make a counter that keeps
            # track of how many random selections it has attempted and just
            # iterates through the cards left over if it goes too high
            card = str(answers[random.randrange(len(answers))])
            if card not in dealt:
                dealt.append(card)
                threads[i].hand.append(card)
                threads[i].send(card.encode('utf-8'))
                # Wait for client to catch up
                # Without this line, the first card received may occasionally be like 200 digits long
                time.sleep(.2)

    print('\n' * 100)
    print('Your hand is: ')
    card = '-1'
    # Deal five cards to self as well
    while card in dealt and len(hand) < 5:
        card = str(answers[random.randrange(460)])
        if card not in dealt:
            dealt.append(card)
            hand.append(card)
    for card in hand:
        print(hand.index(card) + 1, '\t' + card)
    return game_h(name, hand, score)


def game_c(clientsocket, name, hand):
    """The actual game function. Switches between this and dealing for the rest of the game."""

    print(clientsocket.recv(1024).decode('utf8'))
    # Find who is the judge
    judge = clientsocket.recv(1024).decode('utf8')
    print(judge + ' is the judge!\n')

    # If its this client, wait for responses
    if judge == name:
        print("\nPlease wait for all responses.")
    else:
        # Otherwise, send input to the server. If the user plays a card not in their hand, the client
        # will not receive confirmation from the server and will be asked to re-choose
        valid = 'F'
        while valid != 'T':
            try:
                cchoice = int(input("Which card? ")) - 1
                clientsocket.send((str(cchoice) + 'card').encode('utf8'))
                valid = clientsocket.recv(1024).decode('utf8')
                if valid == 'M':
                    # hand.remove(hand[int(cchoice)])
                    hand[int(cchoice)] = 'trash'
            except:
                pass
        # Remove played hand from card
        # hand.remove(hand[int(cchoice)])
        hand[int(cchoice)] = 'trash'
        temp_hand = []
        for i in range(len(hand)):
            if hand[i] != 'trash':
                temp_hand.append(hand[i])
        hand = temp_hand

    # Continue to print out other players as they play cards
    valid = 'F'
    while valid != 'T':
        valid = clientsocket.recv(1024).decode('utf8')
        if valid != 'T':
            print(valid)

    # Print out cards that have been played
    print(clientsocket.recv(1024).decode('utf8'))

    # If this user is judge, they will choose the winning card.
    # Once again, they must choose a card that has been played.
    if judge == name:
        valid = 'F'
        while valid != 'T':
            judge_choice = input("Judge, which card do you choose? ")
            clientsocket.sendall((judge_choice + 'judge').encode('utf8'))
            valid = clientsocket.recv(1024).decode('utf8')
    else:
        print("Please wait for the judge to pick a card. ")

    # This prints the winner after receiving who the winner is from the server
    message = (clientsocket.recv(1024).decode('utf8'))
    print('\n'*100)
    print(message)

    win = clientsocket.recv(1024).decode('utf8')
    if win != 'F':
        print(win)
        time.sleep(5)
        return

    time.sleep(5)
    return deal_c(clientsocket, name, hand)


def game_h(name, hand, score=0):
    """The game, from the server's point of view"""

    global q_card
    global host_card
    winner = ''
    # Clear list of cards that have been played
    del randomize_cards[:]
    # This variable stores the card that the host plays. I'm not sure why I initialized it up here?
    host_sent_card = []
    # Choose question card and send to all clients

    while True:
        q_card = questions[random.randrange(0, len(questions))]
        if q_card not in dealt:
            dealt.append(q_card)
            break

    send_to_all('\n\nQuestion card is: ' + str(q_card))
    print("\nQuestion card is: " + str(q_card))

    # Find out who is judge and send to all clients. If nobody is judge, assume host is judge.
    judge = name
    for i in threads.keys():
        if threads[i].judge:
            judge = threads[i].name
    print(judge + ' is the judge!\n')
    send_to_all(str(judge))

    # If judge, wait for response. Else, take input
    # TODO: Limit host's input to cards in their hand
    if judge == name:
        print("\nPlease wait for all responses.")
        sent = 0
    else:
        while len(host_sent_card) != find_blanks(q_card):
            card_choice = int(input("Which card? "))
            if hand[card_choice - 1] != 'trash':
                host_sent_card.append(card_choice)
        print(name + ' has played their card!')
        # We've seen this before -- tell all users that have already played their card that the host has played theirs.
        for i in threads.keys():
            if threads[i].sent:
                threads[i].send((name + ' has played their card!').encode('utf8'))
        sent = len(host_sent_card)

        for i, j in enumerate(host_sent_card):
            host_sent_card[i] = hand[j - 1]
            # hand.remove(hand[j - 1])
            hand[j - 1] = 'trash'
        temp_hand = []
        for i in range(len(hand)):
            if hand[i] != 'trash':
                temp_hand.append(hand[i])
        hand = temp_hand

    # Wait for all responses to come in
    #print('number to get', (len(threads) * find_blanks(q_card)) - 1)
    if not host_sent_card:
        while sent <= (len(threads) * find_blanks(q_card)) - 1:
            sent = 0
            for i in threads.keys():
                if threads[i].sent:
                    sent += len(threads[i].sent)
    else:
        while sent <= (len(threads) * find_blanks(q_card)) - 1:
            sent = len(host_sent_card)
            for i in threads.keys():
                if threads[i].sent:
                    sent += len(threads[i].sent)

    time.sleep(.2)
    send_to_all('T')

    # Construct message containing all the cards played and sent it to all clients
    message = '\nCards played:\n'

    # Add all cards played to a list and shuffle the list
    for i in threads.keys():
        if threads[i].sent:
            randomize_cards.append(threads[i].sent)
    if host_sent_card:
        randomize_cards.append(host_sent_card)
    random.shuffle(randomize_cards)

    # Create message using shuffled list and send to all clients
    # This way, you can't tell who played what based on the order the cards are printed out.
    for i, n in enumerate(randomize_cards):
        message += str(i + 1)
        for x in n:
            message += ' \t' + str(x) + '\n'
        message += '\n'
    print(message)
    send_to_all(message)

    # If host is judge, they shall judge
    if judge == name:
        judge_choice = None
        # Make sure input is valid
        while judge_choice not in [str(i + 1) for i in range(len(randomize_cards))]:
            judge_choice = input("Judge, which card do you choose? ")
        judge_choice = int(judge_choice)
        # Find user who played the chosen card
        for i in threads.keys():
            if threads[i].sent == randomize_cards[judge_choice - 1]:
                winner = threads[i].name
                threads[i].score += 1
        message = winner + ' has won the round!\n'+q_card+'\n'
        #send_to_all(winner + ' has won the round!')
    # Otherwise, wait for the judge to pick the winner
    else:
        print("Please wait for the judge to pick a card. ")
        # Hey look! This is where the server waits for a client. Once the client chooses the winner, this global
        # variable gets set to true.
        while not host_card:
            pass
        # If the card beloged to the host
        if host_card == 'Host':
            message = name+' has won the round!\n'
            # print(name, 'has won the round!')
            # send_to_all(name + ' has won the round!')
            score += 1
        else:
            message = host_card+' has won the round!\n'
            # print(host_card, 'has won the round!')
            # send_to_all(host_card + ' has won the round!')
        message += q_card+'\n\n'+name+':\n'
        for i in host_sent_card:
            message += i+'\n'

    message += '\n'
    for i in threads.keys():
        if threads[i].sent:
            message += threads[i].name+': '
            for j in threads[i].sent:
                message += '\n'+j
            message += '\n\n'

    print('\n'*100)
    print(message)
    send_to_all(message)
    host_card = False

    if score == 5:
        print(name, 'has won the game!')
        send_to_all(name + ' has won the game!')
        time.sleep(5)
        return

    for i in threads.keys():
        if threads[i].score == 5:
            print(threads[i].name, "has won the game!")
            send_to_all(threads[i].name + " has won the game!")
            time.sleep(5)
            return

    time.sleep(.2)
    send_to_all('F')
    # This isn't so anybody can get caught up, except for slow humans who need to read the output.
    time.sleep(6)

    # Reset all necessary variables in all threads for next round
    # Set next person to be the judge (but it works backwards through the list, because .keys() isn't indexable
    # If it runs into an index error (by trying to set the -1st person to be judge) nobody becomes the judge
    # (which will be interpreted as the host being the judge next round)
    client_judge = False
    for n, i in enumerate(threads.keys()):
        if threads[i].judge:
            client_judge = True
            threads[i].judge = False
            try:
                threads[last_ip].judge = True
            except:
                pass
        # If nobody was the judge, make the last person in the list the judge.
        if n == len(threads.keys()) - 1 and client_judge is False:
            threads[i].judge = True
        last_ip = i
        threads[i].sent = []

    return deal_h(name, hand, score)


# Global variable for when the host has to wait that one time...
host_card = False
# Set up global list for cards played in each round
randomize_cards = []
# Set up global 'cards dealt' list
dealt = ['-1']
# Set up global clients dict
threads = {}
# Global 'found games' list
found_games = []

while True:
    # Fuck look at that sick-ass ASCII art
    # (Sick-AS-CII art)
    print('\n' * 100)
    print("""                                                                                          
             .:+o+/.                        .//                                                     
           `sNNhyymNy`                      /MN                                                     
           yMm.   .yy/ :shhhho` yh/sd/ :yddyyMN -shhhh+`                                            
           MMs        `sy:-:NM+ NMm+:.:NN/-:hMN dMh/:ss-                                            
           dMd`   `yh+`sdyssNM+ NM+   sMd...+MN -oyhhmh:                                            
           .dMdo/+hMd-/MN/:/NM+ NM/   -NMo//dMN yd+-:dMs                                            
            `:oyhys/` `/yys++s/ os-    .oyys/ss .+ssss/`                                            

              /hhs                       hh:                   .//                                  
             .NMNM/    `---`..`  .---.`  ++. ..`.--.   .---.` .+MN.`                                
            `dMy+MN-  :dNdhyNN:`ymhsyNd. NN/ NNhyhNN+ omdsymh.odMMy/                                
            sMN::dMd` NMo..-MM:`/o//oMM/ NM/ MM+  oMm yNds+o/. /MN                                  
           :MMmddmNMs mMs--:MM::mNo+/MM/ NM/ MM/  +Mm -+//sNN+ /MN                                  
          `mNo    /NN:-hmdhyNM::NNsoyNN/ NN/ NN:  +Nm yNhoomm/ :NNy+                                
          `--      --./ss--:MN. .:::..-. --` --`  `--  .:::-`   .-:.                                
           ..`    `.. `+yhhho-                                  `..                                 
           mMh    sMN                                           :md  /hy                            
           mMh    yMN :o/   oo.`oo-oss:-oss/  `/osss/` /o:/sso. -oo +hMNo:.oo`  -o+                 
           mMNddddNMN sMd   NM/-MMy/+MMd//NMo yds-:dMs hMN+/yMN`/MN :yMN:. dMs `mM/                 
           mMd::::hMN sMd   NM/-MM.  NM/  yMy :syyhNMy hMs  .MM./MN  oMm   .NM:sMy                  
           mMh    sMN oMN.`/MM/-MM.  NM/  yMy.MM/..dMy hMs  .MM./MN  oMN.`  /MmMm`                  
           yds    +dh `sdmdohd:.dd`  hd:  odo odmhysds sd+  .dd.:dh  .ydd+   yMM-                   
                                                                           ohNN+                    
                                                                           -:-`
                       Bryce Yoder, Christian Gehman, Nick Walter
""")
    choice = input("Type 'play' to start a game, 'search' to look for open games,"
                   " 'quit' to exit, or type an IP to connect: \n")
    if choice == 'play' or choice == 'Play':  # Open a server if choosing play
        # try:
        server()
        # except:
        #   pass
    elif choice == 'quit' == 'Quit':  # Close program if choosing exit
        quit()
    elif choice == 'search' or choice == 'Search':  # Look for available games if choosing search
        found_games = []
        search()
    else:
        # try:  # Anything else, assume it's an IP and try to connect to it
        client(choice)
        # except:  # If co
        #   pass