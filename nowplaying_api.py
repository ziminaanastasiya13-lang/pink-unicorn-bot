"""
API сервер для Pink Unicorn Radio с постоянным хранением токенов
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import json
import re
import threading
import os
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", 8080))
SPOTIFY_CLIENT_ID = 'f146531bb7924a378c94c672ec31faa3'
SPOTIFY_CLIENT_SECRET = '04d25dc90e9344edbb8f1a4593b3e9e1'
SPOTIFY_REDIRECT = 'https://pink-unicorn-bot-production.up.railway.app/spotify/callback'
TOKENS_FILE = '/tmp/spotify_tokens.json'

# Загружаем токены из файла
def load_tokens():
    try:
        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_tokens(tokens):
    try:
        with open(TOKENS_FILE, 'w') as f:
            json.dump(tokens, f)
    except Exception as e:
        print(f"Ошибка сохранения токенов: {e}")

tokens = load_tokens()

def get_artwork(artist, track):
    try:
        q = requests.utils.quote(f"{artist} {track}")
        r = requests.get(f"https://itunes.apple.com/search?term={q}&media=music&limit=1", timeout=4)
        if r.ok:
            data = r.json()
            if data.get('results'):
                url = data['results'][0].get('artworkUrl100', '')
                if url:
                    return url.replace('100x100bb.jpg', '600x600bb.jpg')
    except:
        pass
    return 'https://static.wixstatic.com/media/6062a7_fbcc0346d0fe43ac8a6e08d6c6b915aa~mv2_d_1750_1750_s_2.png'

def get_now_playing():
    try:
        r = requests.get("https://listen2.myradio24.com/unicorn",
            headers={"User-Agent": "Mozilla/5.0", "Icy-MetaData": "1"},
            stream=True, timeout=5)
        icy_metaint = int(r.headers.get("icy-metaint", 0))
        if icy_metaint > 0:
            r.raw.read(icy_metaint)
            meta_len = ord(r.raw.read(1)) * 16
            if meta_len > 0:
                meta = r.raw.read(meta_len).decode("utf-8", errors="ignore")
                m = re.search(r"StreamTitle='([^']+)'", meta)
                if m:
                    full = m.group(1).strip()
                    d = full.find(" - ")
                    artist = full[:d].strip() if d != -1 else full
                    track = full[d+3:].strip() if d != -1 else ""
                    return {"artist": artist, "track": track, "artwork": get_artwork(artist, track)}
        r.close()
    except Exception as e:
        print(f"ICY ошибка: {e}")
    try:
        r = requests.get("https://onlineradiobox.com/uz/pinkunicorn/playlist/",
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                     "Accept-Language": "ru-RU,ru;q=0.9"}, timeout=5)
        if r.ok:
            m = re.search(r'/track/\d+/">\s*([^<]{5,})\s*</a>', r.text)
            if m:
                full = m.group(1).strip()
                d = full.find(" - ")
                artist = full[:d].strip() if d != -1 else full
                track = full[d+3:].strip() if d != -1 else ""
                return {"artist": artist, "track": track, "artwork": get_artwork(artist, track)}
    except Exception as e:
        print(f"ORB ошибка: {e}")
    return {"artist": "Pink Unicorn Radio", "track": "Live",
            "artwork": "https://static.wixstatic.com/media/6062a7_fbcc0346d0fe43ac8a6e08d6c6b915aa~mv2_d_1750_1750_s_2.png"}

def refresh_token(uid):
    """Обновляем токен если истёк"""
    if uid not in tokens:
        return None
    refresh = tokens[uid].get("refresh")
    if not refresh:
        return None
    try:
        r = requests.post("https://accounts.spotify.com/api/token",
            data={"grant_type": "refresh_token", "refresh_token": refresh,
                  "client_id": SPOTIFY_CLIENT_ID, "client_secret": SPOTIFY_CLIENT_SECRET},
            timeout=5)
        td = r.json()
        if td.get("access_token"):
            tokens[uid]["access"] = td["access_token"]
            if td.get("refresh_token"):
                tokens[uid]["refresh"] = td["refresh_token"]
            save_tokens(tokens)
            return td["access_token"]
    except Exception as e:
        print(f"Refresh ошибка: {e}")
    return None

def spotify_add(uid, artist, track):
    if uid not in tokens:
        return {"error": "not_connected"}
    token = tokens[uid]["access"]
    try:
        q = requests.utils.quote(f"{artist} {track}")
        r = requests.get(f"https://api.spotify.com/v1/search?q={q}&type=track&limit=1",
            headers={"Authorization": f"Bearer {token}"}, timeout=5)
        # Если токен истёк — обновляем
        if r.status_code == 401:
            token = refresh_token(uid)
            if not token:
                del tokens[uid]
                save_tokens(tokens)
                return {"error": "not_connected"}
            r = requests.get(f"https://api.spotify.com/v1/search?q={q}&type=track&limit=1",
                headers={"Authorization": f"Bearer {token}"}, timeout=5)
        items = r.json().get("tracks", {}).get("items", [])
        if not items:
            return {"error": "not_found"}
        uri = items[0]["uri"]
        name = items[0]["name"]
        art = items[0]["artists"][0]["name"]
        me = requests.get("https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {token}"}, timeout=5).json()
        uid_sp = me["id"]
        pls = requests.get(f"https://api.spotify.com/v1/users/{uid_sp}/playlists?limit=50",
            headers={"Authorization": f"Bearer {token}"}, timeout=5).json()
        pl = next((p for p in pls.get("items", []) if p["name"] == "Pink Unicorn Radio"), None)
        if not pl:
            pl = requests.post(f"https://api.spotify.com/v1/users/{uid_sp}/playlists",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"name": "Pink Unicorn Radio", "description": "Треки с Pink Unicorn Radio", "public": False},
                timeout=5).json()
        requests.post(f"https://api.spotify.com/v1/playlists/{pl['id']}/tracks",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"uris": [uri]}, timeout=5)
        return {"ok": True, "track": f"{art} — {name}"}
    except Exception as e:
        return {"error": str(e)}

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        p = parsed.path
        params = parse_qs(parsed.query)

        if p == "/":
            self.send_json(get_now_playing())

        elif p == "/spotify/login":
            uid = params.get("user", ["anon"])[0]
            scope = "playlist-modify-public playlist-modify-private"
            url = (f"https://accounts.spotify.com/authorize"
                   f"?client_id={SPOTIFY_CLIENT_ID}&response_type=code"
                   f"&redirect_uri={requests.utils.quote(SPOTIFY_REDIRECT)}"
                   f"&scope={requests.utils.quote(scope)}&state={uid}")
            self.send_response(302)
            self.send_header("Location", url)
            self.end_headers()

        elif p == "/spotify/callback":
            code = params.get("code", [None])[0]
            state = params.get("state", ["anon"])[0]
            if not code:
                self.send_html("<h2>Ошибка авторизации</h2>")
                return
            try:
                r = requests.post("https://accounts.spotify.com/api/token",
                    data={"grant_type": "authorization_code", "code": code,
                          "redirect_uri": SPOTIFY_REDIRECT,
                          "client_id": SPOTIFY_CLIENT_ID,
                          "client_secret": SPOTIFY_CLIENT_SECRET}, timeout=5)
                td = r.json()
                print(f"Token response: {td}")
                if td.get("access_token"):
                    tokens[state] = {"access": td["access_token"], "refresh": td.get("refresh_token", "")}
                    save_tokens(tokens)
                    print(f"✅ Токен сохранён для {state}")
                    self.send_html("""<!DOCTYPE html><html><head><meta charset='utf-8'>
                    <style>body{background:#0a0010;color:#fff;font-family:sans-serif;
                    display:flex;align-items:center;justify-content:center;min-height:100vh;
                    flex-direction:column;gap:16px;text-align:center;margin:0;padding:20px}</style></head><body>
                    <div style='font-size:60px'>✅</div>
                    <h2 style='color:#1DB954'>Spotify подключён!</h2>
                    <p style='opacity:0.7'>Вернись в Telegram и нажми ❤️ снова</p>
                    </body></html>""")
                else:
                    print(f"❌ Ошибка токена: {td}")
                    self.send_html(f"<h2>Ошибка: {td.get('error_description', 'unknown')}</h2>")
            except Exception as e:
                print(f"❌ Exception: {e}")
                self.send_html(f"<h2>Ошибка: {e}</h2>")

        elif p == "/spotify/check":
            uid = params.get("user", ["anon"])[0]
            self.send_json({"connected": uid in tokens, "uid": uid})

        elif p == "/spotify/add":
            uid = params.get("user", ["anon"])[0]
            artist = params.get("artist", [""])[0]
            track = params.get("track", [""])[0]
            result = spotify_add(uid, artist, track)
            self.send_json(result)
        else:
            self.send_json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass

def run_server():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"API сервер запущен на порту {PORT}")
    server.serve_forever()

thread = threading.Thread(target=run_server, daemon=True)
thread.start()
