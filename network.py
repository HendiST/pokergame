import socket
import threading
import json


class GameServer:
    """Server jalan di HP host (yang hidupkan hotspot)"""

    def __init__(self, port=9999):
        self.port = port
        self.clients = {}       # {player_idx: conn}
        self.num_players = 0
        self.on_action = None   # callback(player_idx, action, data)
        self.running = False
        self.server_sock = None

    def start(self, num_players, on_action):
        self.num_players = num_players
        self.on_action = on_action
        self.running = True
        t = threading.Thread(target=self._listen, daemon=True)
        t.start()

    def _listen(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(('0.0.0.0', self.port))
        self.server_sock.listen(4)
        player_idx = 1  # host = 0, tamu mulai dari 1
        while self.running and player_idx < self.num_players:
            try:
                conn, addr = self.server_sock.accept()
                self.clients[player_idx] = conn
                # Kirim player index ke client
                self.send_to(player_idx, {'type': 'welcome', 'player_idx': player_idx})
                t = threading.Thread(
                    target=self._handle_client,
                    args=(player_idx, conn),
                    daemon=True
                )
                t.start()
                player_idx += 1
            except Exception:
                break

    def _handle_client(self, player_idx, conn):
        buf = ''
        while self.running:
            try:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    break
                buf += data
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    if line.strip():
                        msg = json.loads(line.strip())
                        if self.on_action:
                            self.on_action(player_idx, msg.get('action'), msg.get('data'))
            except Exception:
                break

    def send_to(self, player_idx, msg):
        if player_idx == 0:
            return  # Host terima via callback langsung
        conn = self.clients.get(player_idx)
        if conn:
            try:
                conn.sendall((json.dumps(msg) + '\n').encode('utf-8'))
            except Exception:
                pass

    def broadcast(self, msg):
        for pid in self.clients:
            self.send_to(pid, msg)

    def stop(self):
        self.running = False
        if self.server_sock:
            self.server_sock.close()


class GameClient:
    """Client jalan di HP teman yang konek ke host"""

    def __init__(self):
        self.sock = None
        self.player_idx = None
        self.on_message = None
        self.running = False

    def connect(self, host_ip, port=9999, on_message=None):
        self.on_message = on_message
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host_ip, port))
        self.running = True
        t = threading.Thread(target=self._receive, daemon=True)
        t.start()

    def _receive(self):
        buf = ''
        while self.running:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break
                buf += data
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    if line.strip():
                        msg = json.loads(line.strip())
                        if self.on_message:
                            self.on_message(msg)
            except Exception:
                break

    def send(self, action, data=None):
        msg = {'action': action, 'data': data or {}}
        try:
            self.sock.sendall((json.dumps(msg) + '\n').encode('utf-8'))
        except Exception:
            pass

    def disconnect(self):
        self.running = False
        if self.sock:
            self.sock.close()


def get_local_ip():
    """Dapatkan IP lokal HP (untuk ditampilkan ke host)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'
