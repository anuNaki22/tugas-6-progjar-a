import socket
import os
import json

TARGET_IP = "127.0.0.1"
TARGET_PORT = 8889


class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP,TARGET_PORT)
        self.sock.connect(self.server_address)
        self.tokenid=""
        
    def proses(self,cmdline):
        j=cmdline.split(" ")
        try:
            command=j[0].strip()
            if (command=='auth'):
                username=j[1].strip()
                password=j[2].strip()
                return self.login(username,password)
            elif (command=='register'):
                username=j[1].strip()
                password=j[2].strip()
                nama=j[3].strip()
                negara=j[4].strip()
                return self.register(username, password, nama, negara)
            elif (command=='send'):
                usernameto = j[1].strip()
                message=""
                for w in j[2:]:
                   message="{} {}" . format(message,w)
                return self.sendmessage(usernameto,message)
            elif (command=='buatgroup'):
                nama_group = j[1].strip()
                password = j[2].strip()
                return self.buatgroup(nama_group, password)
            elif (command=='joingroup'):
                nama_group = j[1].strip()
                password = j[2].strip()
                return self.joingroup(nama_group, password)
            elif (command=='inbox'):
                return self.inbox()
            else:
                return "*Maaf, command tidak benar"
        except IndexError:
                return "-Maaf, command tidak benar"
            
    def sendstring(self,string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(64)
                if (data):
                    receivemsg = "{}{}" . format(receivemsg,data.decode())  #data harus didecode agar dapat di operasikan dalam bentuk string
                    if receivemsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock.close()
            return { 'status' : 'ERROR', 'message' : 'Gagal'}
        
    def login(self,username,password):
        string="auth\r\n{}\r\n{}\r\n\r\n" . format(username,password)
        result = self.sendstring(string)
        if result['status']=='OK':
            self.tokenid=result['tokenid']
            return "username {} logged in, token {} " .format(username,self.tokenid)
        else:
            return "Error, {}" . format(result['message'])
        
    def register(self, username, password, nama, negara):
        string = f"register\r\n{username}\r\n{password}\r\n{nama}\r\n{negara}\r\n\r\n"
        print(string)
        result = self.sendstring(string)
        if result['status']=='OK':
            return f"Berhasil buat email {result['email']}"
        else:
            return "Error, {}" . format(result['message'])
        
        
    def sendmessage(self,usernameto="xxx",message="xxx"):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="send\r\n{}\r\n{}\r\n{}\r\n\r\n" . format(self.tokenid,usernameto,message)
        print(string)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "message sent to {}" . format(usernameto)
        else:
            return "Error, {}" . format(result['message'])
    
    def buatgroup(self, nama_group, password):
        if (self.tokenid==""):
            return "Error, not authorized"
        
        string = f"register_group\r\n{self.tokenid}\r\n{nama_group}\r\n{password}\r\n\r\n"
        print(string)
        result = self.sendstring(string)
        if result['status']=='OK':
            return f"email group {result['email_group']}"
        else:
            return "Error, {}" . format(result['message'])
    
    def joingroup(self, nama_group, password):
        if (self.tokenid==""):
            return "Error, not authorized"
        
        string = f"join_group\r\n{self.tokenid}\r\n{nama_group}\r\n{password}\r\n\r\n"
        print(string)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "Berhasil join group"
        else:
            return "Error, {}" . format(result['message'])
        
        
    def inbox(self):
        if (self.tokenid==""):
            return "Error, not authorized"
        string="inbox\r\n{}\r\n\r\n" . format(self.tokenid)
        result = self.sendstring(string)
        if result['status']=='OK':
            return "{}" . format(json.dumps(result['messages']))
        else:
            return "Error, {}" . format(result['message'])



if __name__=="__main__":
    cc = ChatClient()
    while True:
        cmdline = input("Command {}:" . format(cc.tokenid))
        print(cc.proses(cmdline))

