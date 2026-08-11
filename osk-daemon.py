#!/usr/bin/env python3
# Tiny local helper that shows/hides the wvkbd on-screen keyboard on request.
# The browser extension (osk-ext) calls http://127.0.0.1:8577/show when a text
# field is focused and /hide when it loses focus, so the keyboard only occupies
# the screen while you're typing.
import http.server, subprocess, os, threading, glob

PORT = 8577
WVKBD = ["wvkbd-mobintl", "-L", "200", "--fn", "Sans 18"]
_lock = threading.Lock()
_proc = None  # the running wvkbd process, tracked so we can stop and reap it


def _wl_env():
    """Ensure the environment points at the running Wayland session so wvkbd
    (a Wayland client) can connect even if this helper was started without it."""
    env = dict(os.environ)
    xdg = env.get("XDG_RUNTIME_DIR") or ("/run/user/%d" % os.getuid())
    env["XDG_RUNTIME_DIR"] = xdg
    if not env.get("WAYLAND_DISPLAY"):
        socks = [s for s in glob.glob(os.path.join(xdg, "wayland-[0-9]*"))
                 if not s.endswith(".lock")]
        env["WAYLAND_DISPLAY"] = os.path.basename(sorted(socks)[0]) if socks else "wayland-0"
    return env


def show():
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            return  # already visible
        if _proc is not None:
            _proc.wait()  # reap the previous one
        _proc = subprocess.Popen(WVKBD, env=_wl_env(),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def hide():
    global _proc
    with _lock:
        if _proc is None:
            return
        if _proc.poll() is None:
            _proc.terminate()
            try:
                _proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                _proc.kill()
                _proc.wait()
        else:
            _proc.wait()  # reap
        _proc = None


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
