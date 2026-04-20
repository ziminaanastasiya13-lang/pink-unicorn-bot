"""
Простой API сервер — отдаёт "сейчас играет" для Pink Unicorn Radio
Запускается вместе с ботом на Railway
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import json
import re
import threading
import os

PORT = int(os.environ.get("PORT", 8080))

def get_now_playing():
    try:
        r = requests.get(
            "https://onlineradiobox.com/uz/pinkunicorn/playlist/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5
        )
        if r.ok:
            m = re.search(r'/track/\d+/">([^<]{5,})</a>', r.text)
            if m:
                full = m.group(1).strip()
                d = full.find(" - ")
                if d != -1:
                    return {"artist": full[:d].strip(), "track": full[d+3:].strip()}
                return {"artist": full, "track": ""}
    except:
        pass
    return {"artist": "Pink Unicorn Radio", "track": "🎵 Live"}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = get_now_playing()
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # Отключаем логи

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"🌐 API сервер запущен на порту {PORT}")
    server.serve_forever()

# Запуск в отдельном потоке
thread = threading.Thread(target=run_server, daemon=True)
thread.start()
