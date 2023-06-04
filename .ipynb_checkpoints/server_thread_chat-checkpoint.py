from socket import *
import socket
import threading
import time
import sys
import json
import logging
from chat import Chat
from cross_server_connection_thread import ChatNode
from cross_server import CrossServer

class CrossServerQueueGrabber(threading.Thread):
    def __init__(self, queue, chat):
        self.queue = queue
        self.chat = chat
        
        threading.Thread.__init__(self)
        
    def run(self):
        while(True):
            if not self.queue.empty():
                request = self.queue.get()
                
                if (request["command"] == "send"):
                    source = request["source"]
                    destination = request["destination"]
                    message = request["message"]
                    
                    hasil = self.chat.simpan_message(source, destination, message)
                    logging.warning(f"SIMPAN_MESSAGE : {source} mengirim pesan ke {destination} pesan {message} status {hasil}")
                    
                elif (request["command"] == "join_group"):
                    source = request["source"]
                    nama_group = request["nama_group"]
                    password = request["password"]
                    
                    hasil = self.chat.tambah_anggota_group(source, nama_group, password)
                    logging.warning(f"TAMBAH ANGGOTA GROUP : {source} gabung {nama_group} status {hasil}")
            else:
                time.sleep(0.01)

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address, chatserver):
        self.chatserver = chatserver
        
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        rcv=""
        while True:
            data = self.connection.recv(32)
            if data:
                d = data.decode()
                rcv=rcv+d
                if rcv[-4:]=='\r\n\r\n':
                    #end of command, proses string
                    logging.warning("data dari client: {}" . format(rcv))
                    hasil = json.dumps(self.chatserver.proses(rcv))
                    hasil=hasil+"\r\n\r\n"
                    logging.warning("balas ke  client: {}" . format(hasil))
                    self.connection.sendall(hasil.encode())
                    rcv=""
            else:
                break
        self.connection.close()

class Server(threading.Thread):
    def __init__(self, chatserver):
        
        self.chatserver = chatserver
        
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)

    def run(self):
        self.my_socket.bind(('0.0.0.0',8889))
        self.my_socket.listen(1)
        while True:
            self.connection, self.client_address = self.my_socket.accept()
            logging.warning("connection from {}" . format(self.client_address))

            clt = ProcessTheClient(self.connection, self.client_address, self.chatserver)
            clt.start()
            self.the_clients.append(clt)


def main():
    if (len(sys.argv) == 1):
        logging.error("Masukkan domain server pada command")
        return
    
    domain = sys.argv[1]
    
    cross_server = CrossServer(domain)
    chatserver = Chat(domain, cross_server)
    
    chat_node = ChatNode(domain, cross_server)
    chat_node.start()
    
    cross_server_queue_grabber = CrossServerQueueGrabber(cross_server.inbox(), chatserver)
    cross_server_queue_grabber.start()
    
    svr = Server(chatserver)
    svr.start()

if __name__=="__main__":
    main()

