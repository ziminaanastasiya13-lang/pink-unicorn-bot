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
    # Метод 1: ICY метаданные прямо из потока
    try:
        r = requests.get(
            "https://listen2.myradio24.com/unicorn",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Icy-MetaData": "1"
            },
            stream=True,
            timeout=5
        )
        icy_metaint = int(r.headers.get("icy-metaint", 0))
        if icy_metaint > 0:
            # Читаем данные до метаданных
            r.raw.read(icy_metaint)
            meta_len = ord(r.raw.read(1)) * 16
            if meta_len > 0:
                meta = r.raw.read(meta_len).decode("utf-8", errors="ignore")
                m = re.search(r"StreamTitle='([^']+)'", meta)
                if m:
                    full = m.group(1).strip()
                    d = full.find(" - ")
                    if d != -1:
                        return {"artist": full[:d].strip(), "track": full[d+3:].strip()}
                    if full:
                        return {"artist": full, "track": ""}
        r.close()
    except Exception as e:
        print(f"ICY ошибка: {e}")

    # Метод 2: onlineradiobox с другим User-Agent
    try:
        r = requests.get(
            "https://onlineradiobox.com/uz/pinkunicorn/playlist/",
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
                "Accept": "text/html",
                "Accept-Language": "ru-RU,ru;q=0.9",
            },
            timeout=5
        )
        if r.ok:
            m = re.search(r'/track/\d+/">\s*([^<]{5,})\s*</a>', r.text)
            if m:
                full = m.group(1).strip()
                d = full.find(" - ")
                if d != -1:
                    return {"artist": full[:d].strip(), "track": full[d+3:].strip()}
                return {"artist": full, "track": ""}
    except Exception as e:
        print(f"ORB ошибка: {e}")

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
