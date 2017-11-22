from socket import *
serverName = '198.51.243.100'
serverPort = 12000
clientSocket = socket(AF_INET, SOCK_DGRAM)
message = input('Input lcase: ')
clientSocket.sendto(message.encode('utf8'), (serverName, serverPort))
modifiedMessage, addr = clientSocket.recvfrom(2048)
print(modifiedMessage)
clientSocket.close()