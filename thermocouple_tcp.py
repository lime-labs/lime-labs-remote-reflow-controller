# WORK IN PROGRESS!!!

import socket, struct

def getTempFromThermocouple(ip, port, unit):

    # Send command and receive reply
    try:
        sock_tcp = socket.socket()
        sock_tcp.connect((ip, port))
        #sock_tcp.send(unit)
        data = sock_tcp.recv(256)
        sock_tcp.close()

        print(data)
        result = struct.unpack('f', data)
        return result

    except socket.error:
        print("Could not connect to thermocouple at " + ip + ":" + str(port))
