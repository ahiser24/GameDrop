"""
Discord OAuth2 integration for Game Drop.
Implements the Implicit Grant Flow for authenticating users.
"""
import http.server
import urllib.parse
import webbrowser
import json
import requests
import os
import logging
import platform
from gamedrop.utils.paths import get_logs_directory

logger = logging.getLogger("GameDrop.DiscordOAuth")

CLIENT_ID = "1461922623142498346"
REDIRECT_URI = "http://127.0.0.1:8457/callback"
AUTH_URL = f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&response_type=token&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&scope=identify"

class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/callback":
            if "access_token" in parsed.query:
                # Part 2: JS redirected with token
                query_params = urllib.parse.parse_qs(parsed.query)
                self.server.access_token = query_params.get("access_token", [None])[0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Successfully authenticated!</h1><p>You can close this window and return to Game Drop.</p><script>window.close()</script></body></html>")
            else:
                # Part 1: First hit from Discord Auth (token is in hash)
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html = """
                <html><body>
                <p>Authenticating...</p>
                <script>
                    if (window.location.hash) {
                        var hash = window.location.hash.substring(1);
                        window.location.replace('/callback?' + hash);
                    } else {
                        document.body.innerHTML = 'Authentication failed or was cancelled.';
                    }
                </script>
                </body></html>
                """
                self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class DiscordOAuth:
    def __init__(self):
        if platform.system() == "Windows":
            self.token_file = os.path.join(os.getenv('APPDATA', get_logs_directory()), 'GameDrop', 'discord_token.json')
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        else:
            self.token_file = os.path.join(get_logs_directory(), 'discord_token.json')
            
        self.access_token = None
        self.user_info = None
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.user_info = data.get('user_info')
            except Exception as e:
                logger.error(f"Error loading auth cache: {e}")

    def save_cache(self):
        try:
            with open(self.token_file, 'w') as f:
                json.dump({'access_token': self.access_token, 'user_info': self.user_info}, f)
        except Exception as e:
            logger.error(f"Error saving auth cache: {e}")

    def is_authenticated(self):
        return self.access_token is not None and self.user_info is not None

    def logout(self):
        self.access_token = None
        self.user_info = None
        if os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
            except OSError:
                pass

    def start_auth(self):
        try:
            server = http.server.HTTPServer(('127.0.0.1', 8457), OAuthCallbackHandler)
        except OSError as e:
            logger.error(f"Could not start auth server: {e}")
            return False
            
        server.access_token = None
        server.timeout = 120 # 2 minute timeout
        
        webbrowser.open(AUTH_URL)
        
        # Wait for callback (part 1)
        server.handle_request()
        if not server.access_token:
            # Wait for redirect (part 2)
            server.handle_request()
            
        self.access_token = server.access_token
        server.server_close()
        
        if self.access_token:
            return self.fetch_user_info()
        return False

    def fetch_user_info(self):
        url = "https://discord.com/api/users/@me"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            user_data = r.json()
            
            avatar_url = None
            if user_data.get('avatar'):
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png"
                
            self.user_info = {
                'id': user_data['id'],
                'username': user_data['username'],
                'avatar_url': avatar_url
            }
            self.save_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to fetch user info: {e}")
            self.access_token = None
            return False

    def get_cached_user(self):
        return self.user_info
