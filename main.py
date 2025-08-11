import http.server
import socketserver
import socket
import threading
import json
from urllib.parse import parse_qs
from pathlib import Path
from datetime import datetime

# Константи
HOST = '127.0.0.1'
HTTP_PORT = 3000
SOCKET_PORT = 5000

# Шляхи
BASE_DIR = Path(__file__).parent
TEMPLATES = BASE_DIR / 'templates'
STATIC = BASE_DIR / 'static'
STORAGE = BASE_DIR / 'storage'
DATA_FILE = STORAGE / 'data.json'


# HTTP сервер
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/':
            self.serve_file(TEMPLATES / 'index.html', content_type='text/html')
        elif path == '/message' or path == '/message.html':
            self.serve_file(TEMPLATES / 'message.html', content_type='text/html')
        elif path == '/error.html':
            self.serve_file(TEMPLATES / 'error.html', content_type='text/html')
        elif path.startswith('/static/'):
            file_path = STATIC / path[len('/static/'):]
            if file_path.exists():
                content_type = self.get_content_type(file_path)
                self.serve_file(file_path, content_type)
            else:
                self.serve_404()
        else:
            self.serve_404()

    def do_POST(self):
        if self.path == '/message':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode()
            data = parse_qs(body)
            username = data.get("username", [""])[0]
            message = data.get("message", [""])[0]

            payload = json.dumps({
                "username": username,
                "message": message
            })

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload.encode(), (HOST, SOCKET_PORT))

            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.serve_404()

    # Віддає файл
    def serve_file(self, file_path: Path, content_type='text/html'):
        try:
            with open(file_path, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.serve_404()

    # Віддає 404
    def serve_404(self):
        error_path = TEMPLATES / 'error.html'
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(error_path.read_bytes())

    # Визначає тип контенту
    def get_content_type(self, path: Path):
        if path.suffix == '.css':
            return 'text/css'
        elif path.suffix == '.png':
            return 'image/png'
        elif path.suffix == '.js':
            return 'application/javascript'
        else:
            return 'application/octet-stream'


# UDP сокет сервер
def socket_server():
    STORAGE.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text('{}')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, SOCKET_PORT))
    print(f"[Socket] Listening on {HOST}:{SOCKET_PORT}")

    while True:
        data, _ = sock.recvfrom(4096)
        try:
            message = json.loads(data.decode('utf-8'))
            timestamp = str(datetime.now())
            current_data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
            current_data[timestamp] = message
            DATA_FILE.write_text(json.dumps(current_data, indent=2), encoding='utf-8')
            print(f"[Socket] Message saved at {timestamp}")
        except Exception as e:
            print(f"[Socket] Error: {e}")

# Запуск HTTP сервера
def start_http_server():
    with socketserver.ThreadingTCPServer((HOST, HTTP_PORT), CustomHandler) as httpd:
        print(f"[HTTP] Serving on http://{HOST}:{HTTP_PORT}")
        httpd.serve_forever()


def main():
    udp_thread = threading.Thread(target=socket_server, daemon=True)
    udp_thread.start()

    start_http_server()


if __name__ == '__main__':
    main()