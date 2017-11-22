import socket
import re
from urllib import request
from xml.dom.minidom import parseString

req = "M-SEARCH * HTTP/1.1\r\n" + \
            "HOST: 239.255.255.250:1900\r\n" + \
            "MAN: \"ssdp:discover\"\r\n" + \
            "MX: 2\r\n" + \
            "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n" + '\r\n'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2)
sock.sendto(req.encode('utf8'), ('239.255.255.250', 1900))

data = sock.recv(1000).decode('utf8')
print(data)

parsed = re.findall(r'(?P<name>.*?): (?P<value>.*?)\r\n', data)
location = parsed[1][1]

directory = request.urlopen(location).read()
dom = parseString(directory)

service_types = dom.getElementsByTagName('serviceType')

for service in service_types:
    if service.childNodes[0].data.find('WANIPConnection') > 0:
        path = service.parentNode.getElementsByTagName('controlURL')[0].childNodes[0].data

print(path)