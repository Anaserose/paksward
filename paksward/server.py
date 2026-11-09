"""A small web server that only this computer can reach. It serves the interface in frontend/ and
answers /api/<method> calls from the page.

Why it is safe to run on a personal machine:
* it binds to 127.0.0.1, so other devices on the network cannot connect;
* every API call needs a random token that exists only in the link printed at start-up, which stops
  other web pages open in your browser from talking to it (they cannot know the token);
* the Host and Origin headers are checked, which blocks DNS-rebinding tricks;
* only a fixed set of file types can be served from frontend/, and paths cannot escape that folder.
"""
import hmac
import json
import os
import posixpath
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from . import config
from .api import Api, Locked, PUBLIC

FRONTEND_DIR = config.FRONTEND_DIR
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon"}
MAX_BODY = 4_000_000
# Nothing may load from outside this computer: no fonts, scripts, images or connections.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'none'; "
       "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class PakswardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, api: Api, token: str = None, port: int = 0, frontend_dir: str = FRONTEND_DIR):
        super().__init__(("127.0.0.1", port), Handler)
        self.api, self.frontend_dir = api, os.path.realpath(frontend_dir)
        self.token = token or secrets.token_urlsafe(32)
        p = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{p}", f"localhost:{p}"}


    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/#t={self.token}"


class Handler(BaseHTTPRequestHandler):
    server_version = "Paksward"
    sys_version = ""
    timeout = 15                        # drop connections that stall instead of holding a thread forever

    def log_message(self, *args):          # keep the terminal quiet; never log request bodies
        pass

    # ---- helpers ----
    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        self.send_header("Content-Security-Policy", CSP)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode("utf-8"))

    def _host_ok(self):
        return self.headers.get("Host", "") in self.server.allowed_hosts

    # ---- static files ----
    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"ok": False, "error": "Forbidden"})
        path = posixpath.normpath(unquote(urlsplit(self.path).path))
        rel = "index.html" if path in ("/", ".") else path.lstrip("/")
        full = os.path.realpath(os.path.join(self.server.frontend_dir, rel))
        ext = os.path.splitext(full)[1].lower()
        inside = full.startswith(self.server.frontend_dir + os.sep)
        if not inside or ext not in TYPES or not os.path.isfile(full):
            return self._json(404, {"ok": False, "error": "Not found"})
        with open(full, "rb") as f:
            data = f.read()
        if os.path.basename(full) == "index.html":      # tell the page it is talking to the real backend
            data = data.replace(b"</head>", b'<meta name="paksward-server" content="1">\n</head>', 1)
        self._send(200, data, TYPES[ext])

    # ---- API ----
    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"ok": False, "error": "Forbidden"})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{h}" for h in self.server.allowed_hosts}:
            return self._json(403, {"ok": False, "error": "Forbidden"})
        if not hmac.compare_digest(self.headers.get("X-Paksward-Token", "").encode("utf-8"), self.server.token.encode("utf-8")):
            return self._json(401, {"ok": False, "error": "Session expired. Open Paksward from the link in your terminal."})
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._json(415, {"ok": False, "error": "Unsupported"})
        path = urlsplit(self.path).path
        name = path[5:] if path.startswith("/api/") else ""
        if name == "quit":                      # lets a double-clicked app (no terminal) be closed from its own window
            self.server.api.lock()
            self._json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if name not in PUBLIC:
            return self._json(404, {"ok": False, "error": "Unknown method"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_BODY:
                return self._json(413, {"ok": False, "error": "Too large"})
            payload = json.loads(self.rfile.read(length) or b"{}")
            args = payload.get("args", [])
            if not isinstance(args, list):
                raise ValueError
        except (ValueError, TypeError):
            return self._json(400, {"ok": False, "error": "Bad request"})
        try:
            api = self.server.api
            if name in api.SLOW_CALLS:             # manages the lock itself so a slow network call cannot block Lock
                result = getattr(api, name)(*args)
            else:
                with api.mutex:                    # the Api is not thread-safe, so other calls run one at a time
                    result = getattr(api, name)(*args)
        except Locked:
            return self._json(200, {"ok": False, "locked": True, "error": "The vault is locked."})
        except TypeError:
            return self._json(400, {"ok": False, "error": "Bad arguments"})
        except Exception as exc:               # never echo details: they could contain secrets
            print(f"paksward: error in {name}: {type(exc).__name__}", file=sys.stderr)
            return self._json(500, {"ok": False, "error": "Something went wrong. Your vault was not changed."})
        self._json(200, result)
