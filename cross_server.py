import sys
import os
import time
import logging
import uuid
import json
import re
from queue import Queue

class CrossServer():
    def __init__(self, domain):
        self.domains = {
            "mail.com" : {"password" : "mail" },
            "surat.com" : {"password" : "surat" },
            "merpati.com" : {"password" : "merpati" }
        }
        
        self.domain = domain
        self.bank_socket = {}
        self.sessions = {}
        self.queue = Queue()
    
    def proses(self,data):
        j=data.split("\r\n")
        try:
            command=j[0].strip()
            if (command=='auth'):
                domain=j[1].strip()
                password=j[2].strip()
                logging.warning("AUTH CROSS SERVER: auth {} {}" . format(domain, password))
                return self.autentikasi_user(domain, password)
            elif (command=='send'):
                sessionid = j[1].strip()
                source_email = j[2].strip()
                destination_email = j[3].strip()
                message = j[4].strip()
                return self.send(sessionid, source_email, destination_email, message)
            elif (command=='join_group'):
                sessionid = j[1].strip()
                source_email = j[2].strip()
                nama_group = j[3].strip()
                password = j[4].strip()
                return self.join_group(sessionid, source_email, nama_group, password)
                
            else:
                return {'status': 'ERROR', 'message': '**Protocol Tidak Benar'}
        except KeyError:
            return { 'status': 'ERROR', 'message' : 'Informasi tidak ditemukan'}
        except IndexError:
            return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}
        
    def set_koneksi(self, domain, koneksi, token):
        self.bank_socket[domain] = { "socket" : koneksi, "tokenid" : token }
        
    def ambil_koneksi(self, domain):
        if domain not in self.bank_socket:
            return False
        return self.bank_socket[domain]
    
    def autentikasi_user(self, domain, password):
        if domain not in self.domains:
            return { 'status': 'ERROR', 'message': 'Domain Tidak Tersedia' }
        
        tokenid = str(uuid.uuid4())
        self.sessions[tokenid] = { 'domain': domain }
        return { 'status': 'OK', 'tokenid': tokenid }
    
    def send(self, sessionid, source_email, destionation_email, message):
        if sessionid != None and sessionid not in self.sessions:
            return { 'status': 'ERROR', 'message': 'Session Tidak Ditemukan' }
        
        domain_destinasi = self.get_domain(destionation_email)
        
        if domain_destinasi == None:
            return { 'status': 'ERROR', 'message': 'Email Salah' }
        
        elif domain_destinasi == self.domain:
            self.queue.put({ "command" : "send", "source" : source_email, "destination" : destionation_email, "message" : message})
            
        elif domain_destinasi in self.bank_socket:
            sock = self.bank_socket[domain_destinasi]["socket"]
            try:
                sock.sendall(f"send\r\n{self.bank_socket[domain_destinasi]['tokenid']}\r\n{source_email}\r\n{destionation_email}\r\n{message}\r\n\r\n".encode())
                hasil = ""
                while True:
                    data = sock.recv(64)

                    if (data):
                        hasil += data.decode()
                    else:
                        break
                        
                    if (hasil[-4:] == "\r\n\r\n"):
                        hasil_json = json.loads(hasil)
                        logging.warning(hasil_json)
                        break
                        
            except Exception as e:
                logging.warning(e)
                try:
                    sock.close()
                    sock.shutdown()
                except:
                    pass
                self.bank_socket[domain_destinasi]["socket"] = None
        
        else:
            return { 'status': 'ERROR', 'message': 'Tidak Dapat Meneruskan' }
        
        return { 'status': 'OK' }
        
    def join_group(self, sessionid, source_email, nama_group, password):
        if sessionid != None and sessionid not in self.sessions:
            return { 'status': 'ERROR', 'message': 'Session Tidak Ditemukan' }
        
        domain_destinasi = self.get_domain(nama_group)
        
        if domain_destinasi == None:
            return { 'status': 'ERROR', 'message': 'Email Salah' }
        
        elif domain_destinasi == self.domain:
            self.queue.put({ "command" : "join_group", "source" : source_email, "nama_group" : nama_group, "password" : password })
            
        elif domain_destinasi in self.bank_socket:
            sock = self.bank_socket[domain_destinasi]["socket"]
            try:
                sock.sendall(f"join_group\r\n{self.bank_socket[domain_destinasi]['tokenid']}\r\n{source_email}\r\n{nama_group}\r\n{password}\r\n\r\n".encode())
                hasil = ""
                while True:
                    data = sock.recv(64)

                    if (data):
                        hasil += data.decode()
                    else:
                        break
                        
                    if (hasil[-4:] == "\r\n\r\n"):
                        hasil_json = json.loads(hasil)
                        logging.warning(hasil_json)
                        break
            except Exception as e:
                try:
                    sock.close()
                    sock.shutdown()
                except:
                    pass
                self.bank_socket[domain_destinasi]["socket"] = None
        
        else:
            return { 'status': 'ERROR', 'message': 'Tidak Dapat Meneruskan' }
        return { 'status': 'OK' }
    
    def inbox(self): 
        return self.queue
    
    def is_email(self, email):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None
    
    def get_domain(self, email):
        if self.is_email(email):
            pattern = r"(?<=@)(\S+)"
            return re.search(pattern, email).group()
        return None