import socket
import threading
import json
import base64
import hashlib
import time
import sqlite3

from config import DB_FILE

class WebSocketServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients = {}
        self.match_broadcasters = {}
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(5)
        print(f"🔥 WebSocket сервер запущен на ws://{self.host}:{self.port}")
        
        while True:
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client,)).start()
    
    def handle_client(self, client):
        try:
            data = client.recv(1024).decode()
            if 'Sec-WebSocket-Key' in data:
                key_line = [line for line in data.split('\r\n') if 'Sec-WebSocket-Key:' in line][0]
                key = key_line.split(': ')[1]
                
                accept_key = base64.b64encode(
                    hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
                ).decode()
                
                response = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {accept_key}\r\n\r\n"
                )
                client.send(response.encode())
                
                while True:
                    try:
                        msg = self.receive_message(client)
                        if msg:
                            self.process_message(client, msg)
                    except:
                        break
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.remove_client(client)
    
    def process_message(self, client, message):
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'auth':
                user_id = data.get('user_id')
                self.clients[client] = {'user_id': user_id}

                match_id = data.get('match_id')
                if match_id:
                    self.clients[client]['match_id'] = match_id

                    if match_id not in self.match_broadcasters:
                        self.match_broadcasters[match_id] = []
                    if client not in self.match_broadcasters[match_id]:
                        self.match_broadcasters[match_id].append(client)
                
            elif msg_type == 'answer_submitted':
                match_id = data.get('match_id')
                user_id = data.get('user_id')
                self.broadcast_to_match(match_id, {
                    'type': 'answer_submitted',
                    'user_id': user_id,
                    'timestamp': time.time()
                }, exclude_client=client)
                
            elif msg_type == 'chat':
                match_id = data.get('match_id')
                message = data.get('message')
                self.broadcast_to_match(match_id, {
                    'type': 'chat',
                    'user_id': self.clients[client]['user_id'],
                    'message': message,
                    'timestamp': time.time()
                })
                
        except json.JSONDecodeError:
            pass
    
    def broadcast_to_match(self, match_id, message, exclude_client=None):
        if match_id in self.match_broadcasters:
            msg_json = json.dumps(message)
            for client_socket in self.match_broadcasters[match_id]:
                if client_socket != exclude_client:
                    try:
                        self.send_message(client_socket, msg_json)
                    except:
                        pass
    
    def receive_message(self, client):
        try:
            data = client.recv(2)
            if len(data) < 2:
                return None
            
            first_byte, second_byte = data[0], data[1]
            masked = (second_byte & 0x80) != 0
            payload_length = second_byte & 0x7F
            
            if payload_length == 126:
                data += client.recv(2)
                payload_length = int.from_bytes(data[2:4], 'big')
            elif payload_length == 127:
                data += client.recv(8)
                payload_length = int.from_bytes(data[2:10], 'big')
            
            if masked:
                mask_key = client.recv(4)
                encoded = client.recv(payload_length)
                decoded = bytes(encoded[i] ^ mask_key[i % 4] for i in range(len(encoded)))
            else:
                decoded = client.recv(payload_length)
            
            return decoded.decode('utf-8')
        except:
            return None
    
    def send_message(self, client, message):
        try:
            header = bytearray()
            header.append(0x81)
            
            msg_bytes = message.encode('utf-8')
            length = len(msg_bytes)
            
            if length <= 125:
                header.append(length)
            elif length <= 65535:
                header.append(126)
                header.extend(length.to_bytes(2, 'big'))
            else:
                header.append(127)
                header.extend(length.to_bytes(8, 'big'))
            
            client.send(header + msg_bytes)
        except:
            pass
    
    def remove_client(self, client):
        if client in self.clients:
            client_info = self.clients[client]
            match_id = client_info.get('match_id')
            
            if match_id and match_id in self.match_broadcasters:
                if client in self.match_broadcasters[match_id]:
                    self.match_broadcasters[match_id].remove(client)
                
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT username FROM users WHERE id = ?", (client_info['user_id'],))
                username = cursor.fetchone()[0]
                conn.close()

                self.broadcast_to_match(match_id, {
                    'type': 'player_left',
                    'user_id': client_info['user_id'],
                    'username': username,
                    'timestamp': time.time()
                })
            
            del self.clients[client]
        client.close()
