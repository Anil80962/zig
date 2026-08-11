#!/usr/bin/env python3
# Tiny local helper that shows/hides the wvkbd on-screen keyboard on request.
# The browser extension (osk-ext) calls http://127.0.0.1:8577/show when a text
# field is focused and /hide when it loses focus. Showing = start wvkbd,
# hiding = kill it, so the keyboard only occupies the screen when needed.
import http.server, subprocess, os, threading

PORT = 8577
WVKBD = ["wvkbd-mobintl", "-L", "200", "--fn", "Sans 18"]
_lock = threading.Lock()


def _running():
    return subprocess.run(["pgrep", "-x", "wvkbd-mobintl"],
                          stdout=subprocess.DEVNULL).returncode == 0


def show():
    with _lock:
        if not _running():
            subprocess.Popen(WVKBD, env=dict(os.environ),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def hide():
    with _lock:
        subprocess.run(["pkill", "-x", "wvkbd-mobintl"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/show"):
            show()
        elif self.path.startswith("/hide"):
            hide()
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
