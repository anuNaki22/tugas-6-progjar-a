import sys
import threading
import os
import json
import uuid
import logging
import re
from queue import  Queue

class Chat:
    def __init__(self, domain, cross_server):
        self.domain = domain
        self.sessions={}
        self.emails = {}
        self.users = {}
        self.groups = {}
        
        self.cross_server = cross_server
        
    def proses(self,data):
        j=data.split("\r\n")
        try:
            command=j[0].strip()
            if (command=='register'):
                username=j[1].strip()
                password=j[2].strip()
                nama=j[3].strip()
                negara=j[4].strip()
                logging.warning("REGISTER: auth {} {} nama {} asal {}" . format(username, password, nama, negara))
                return self.register_user(username, password, nama, negara)

            elif (command=='auth'):
                username=j[1].strip()
                password=j[2].strip()
                logging.warning("AUTH: auth {} {}" . format(username,password))
                return self.autentikasi_user(username,password)
            
            elif (command=='register_group'):
                sessionid = j[1].strip()
                nama_group = j[2].strip()
                password = j[3].strip()
                logging.warning("REGISTER_GROUP: session {} membuat group {} password {}" . format(sessionid, nama_group, password))
                return self.buat_group(sessionid, nama_group, password)
            
            elif (command=='join_group'):
                sessionid = j[1].strip()
                nama_group = j[2].strip()
                password = j[3].strip()
                logging.warning("JOIN_GROUP: session {} join group {} password {}" . format(sessionid, nama_group, password))
                return self.join_group(sessionid, nama_group, password)
                
            elif (command=='send'):
                sessionid = j[1].strip()
                email_destination = j[2].strip()
                message= j[3].strip()
                logging.warning("SEND: session {} send message to {}" . format(sessionid, email_destination))
                
                return self.send_message(sessionid, email_destination, message)
            
            elif (command=='inbox'):
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOX: {}" . format(sessionid))
                return self.get_inbox(username)
            
            else:
                return {'status': 'ERROR', 'message': '**Protocol Tidak Benar'}
        except KeyError:
            return { 'status': 'ERROR', 'message' : 'Informasi tidak ditemukan'}
        except IndexError:
            return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}
    
    def validasi_username(self, username):
        pattern = r'^[A-Za-z0-9._%+-]+$'
        return re.match(pattern, username) is not None
    
    def register_user(self, username, password, nama, negara):
        if (not self.validasi_username(username)):
            return { 'status': 'ERROR', 'message': 'Format Username Tidak Sesuai' }
        
        username += "@"+self.domain
        if (username in self.users):
            return { 'status': 'ERROR', 'message': 'Username Telah Dipakai' }
        
        self.emails[username]={ 'password': password, 'type': 'personal'}
        self.users[username] = {'nama': nama, 'negara': negara, 'incoming' : {}, 'outgoing': {}}
        return { 'status': 'OK', 'email': username }
        
        
    def autentikasi_user(self,username,password):
        username += "@"+self.domain
        
        if (username not in self.users):
            return { 'status': 'ERROR', 'message': 'User Tidak Ada' }
        
        if (self.emails[username]['password'] != password):
            return { 'status': 'ERROR', 'message': 'Password Salah' }
        
        tokenid = str(uuid.uuid4())
        self.sessions[tokenid]={ 'username': username, 'userdetail':self.users[username] }
        return { 'status': 'OK', 'tokenid': tokenid }
    
    def buat_group(self, sessionid, nama_group, password):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
        if (not self.validasi_username(nama_group)):
            return { 'status': 'ERROR', 'message': 'Format Nama Group Tidak Sesuai' }
        
        nama_group +="@"+self.domain
        
        if (nama_group in self.groups):
            return {'status': 'ERROR', 'message': 'Nama Telah Dipakai'}
        
        self.emails[nama_group] = { 'password' : password, 'type' : 'group' }
        self.groups[nama_group] = { 'member' : { self.sessions[sessionid]["username"] } }
        return {'status': 'OK', 'email_group' : nama_group }
        
    def join_group(self, sessionid, nama_group, password):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
        email_source = self.sessions[sessionid]["username"]
        self.cross_server.join_group(None, email_source, nama_group, password)
        return {'status': 'OK'}
    
    def tambah_anggota_group(self, email, nama_group, password):
        
        if (nama_group not in self.groups):
            return {'status': 'ERROR', 'message': 'Group Tidak Ada'}
        
        if (email in self.groups[nama_group]['member']):
            return {'status': 'ERROR', 'message': 'Sudah Tergabung Dalam Group'}
        
        self.groups[nama_group]['member'].add(email)
        return {'status': 'OK'}
    
    def get_user(self,username):
        if (username not in self.users):
            return False
        return self.users[username]
    
    def get_type(self, username):
        if username not in self.emails:
            return False
        return self.emails[username]['type']
    
    def is_email(self, email):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None
    
    def get_email_from_session(self, session):
        if (session not in self.sessions):
            return False
        return self.sessions[session]['username']
    
    def group_member(self, nama_group):
        if nama_group not in self.groups:
            return False
        return self.groups[nama_group]["member"]
    
    def simpan_message(self, source_email, destination_email, message):
        
        email_type = self.get_type(destination_email)
        
        logging.warning(f"MASUK SINI {destination_email} {email_type}")
        
        if email_type == False:
            return
        
        if email_type == "personal" and destination_email in self.users:
            data_destinasi = self.get_user(destination_email)
            inqueue_receiver = data_destinasi['incoming']
            try:
                inqueue_receiver[source_email].put(message)
            except KeyError:
                inqueue_receiver[source_email]=Queue()
                inqueue_receiver[source_email].put(message)
                
        elif email_type == "group" and destination_email in self.groups:
            member = self.group_member(destination_email)
            
            if source_email in member:
                for email_member in member:
                    if email_member != source_email:
                        self.cross_server.send(None, destination_email, email_member, message)
            
    
    def send_message(self, sessionid, email_destination, message):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        
        if (not self.is_email(email_destination)):
            return {'status': 'ERROR', 'message': 'Alamat Destinasi Tidak Benar'}
        
        email_from = self.get_email_from_session(sessionid)
        data_pengirim = self.get_user(email_from)

        message_json = { 'msg_from': "{}({})" .format(data_pengirim['nama'], email_from), 'msg_to': "{}".format(email_destination), 'msg': message }
        message = json.dumps(message_json)
        
        self.cross_server.send(None, email_from, email_destination, message)
        
        outqueue_sender = data_pengirim['outgoing']
        try:
            outqueue_sender[email_destination].put(message)
        except KeyError:
            outqueue_sender[email_destination]=Queue()
            outqueue_sender[email_destination].put(message)
        
        return {'status': 'OK', 'message': 'Message Sent'}

    def get_inbox(self,username):
        s_fr = self.get_user(username)
        incoming = s_fr['incoming']
        msgs={}
        for users in incoming:
            msgs[users]=[]
            while not incoming[users].empty():
                msgs[users].append(s_fr['incoming'][users].get_nowait())

        return {'status': 'OK', 'messages': msgs}


if __name__=="__main__":
    domain = "tes.com"
    
    
    from cross_server import CrossServer 
    from server_thread_chat import CrossServerQueueGrabber
    
    cross_server = CrossServer(domain)
    j = Chat(domain, cross_server)
    
    cross_server_queue_grabber = CrossServerQueueGrabber(cross_server.inbox(), j)
    cross_server_queue_grabber.start()
    
    # sesi = j.proses("auth messi surabaya")
    # print(sesi)
    # #sesi = j.autentikasi_user('messi','surabaya')
    # #print sesi
    # tokenid = sesi['tokenid']
    # print(j.proses("send {} henderson hello gimana kabarnya son " . format(tokenid)))
    # print(j.proses("send {} messi hello gimana kabarnya mess " . format(tokenid)))

    #print j.send_message(tokenid,'messi','henderson','hello son')
    #print j.send_message(tokenid,'henderson','messi','hello si')
    #print j.send_message(tokenid,'lineker','messi','hello si dari lineker')


    # print("isi mailbox dari messi")
    # print(j.get_inbox('messi'))
    # print("isi mailbox dari henderson")
    # print(j.get_inbox('henderson'))
    
    users = [
        {"username" : "satu", "password" : "satu", "nama" : "satu", "negara" : "Indonesia"},
        {"username" : "dua", "password" : "dua", "nama" : "dua", "negara" : "Indonesia"},
        {"username" : "tiga", "password" : "tiga", "nama" : "tiga", "negara" : "Indonesia"}
    ]
    
    for user in users:
        print(j.proses(f"register\r\n{user['username']}\r\n{user['password']}\r\n{user['nama']}\r\n{user['negara']}\r\n\r\n"))
        
    print(j.emails)
        
    token = {}
    for user in users:
        res = j.proses(f"auth\r\n{user['username']}\r\n{user['password']}\r\n\r\n")
        print(res)
        token[user['username']] = res['tokenid']
        
    pesan = [
        f"send\r\n{token[users[0]['username']]}\r\n{users[1]['username']+'@'+domain}\r\nDARI SATU MENUJU DUA\r\n\r\n",
        f"send\r\n{token[users[1]['username']]}\r\n{users[0]['username']+'@'+domain}\r\nDARI DUA MENUJU SATU\r\n\r\n",
    ]
    
    for p in pesan:
        print(j.proses(p))
    
    import time
    
    time.sleep(1)
    
    for user in users:
        print(f"inbox {user['username']+'@'+domain}:")
        print(j.proses(f"inbox\r\n{token[user['username']]}"))
    
    buat_group = f"register_group\r\n{token[users[0]['username']]}\r\nbilangan\r\nangka\r\n\r\n"
    print(j.proses(buat_group))
    
    join_group = f"join_group\r\n{token[users[1]['username']]}\r\n{'bilangan@'+domain}\r\nangka\r\n\r\n"
    print(j.proses(join_group))
    
    pesan_group_member = f"send\r\n{token[users[1]['username']]}\r\n{'bilangan@'+domain}\r\nDARI DUA MENUJU SEMUA ANGGOTA GRUP BILANGAN\r\n\r\n"
    print(j.proses(pesan_group_member))
    
    pesan_group_non_member = f"send\r\n{token[users[2]['username']]}\r\n{'bilangan@'+domain}\r\nDARI TIGA MENUJU SEMUA ANGGOTA GRUP BILANGAN YANG SEHARUSNYA TIDAK BERHASIL\r\n\r\n"
    print(j.proses(pesan_group_non_member))
    
    
    
    time.sleep(1)
    
    for user in users:
        print(f"inbox {user['username']+'@'+domain}:")
        print(j.proses(f"inbox\r\n{token[user['username']]}"))
    
    print(j.users)
    
    join_group = f"join_group\r\n{token[users[2]['username']]}\r\n{'bilangan@'+domain}\r\nangka\r\n\r\n"
    print(j.proses(join_group))
    
    pesan_group_member = f"send\r\n{token[users[0]['username']]}\r\n{'bilangan@'+domain}\r\nDARI SATU MENUJU SEMUA ANGGOTA GRUP BILANGAN\r\n\r\n"
    print(j.proses(pesan_group_member))
    
    pesan_group_member = f"send\r\n{token[users[1]['username']]}\r\n{'bilangan@'+domain}\r\nDARI DUA MENUJU SEMUA ANGGOTA GRUP BILANGAN\r\n\r\n"
    print(j.proses(pesan_group_member))
    
    time.sleep(1)
    
    for user in users:
        print(f"inbox {user['username']+'@'+domain}:")
        print(j.proses(f"inbox\r\n{token[user['username']]}"))
    
    print(j.users)
    
    