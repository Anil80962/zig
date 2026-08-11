#!/usr/bin/env python3
# Tiny WiFi manager for the kiosk. Opened by the WiFi icon on the AquaGen page.
# Scans networks (plain nmcli) and connects (sudo nmcli). Touch-friendly, sized
# for the 7" screen. Requires: /etc/sudoers.d/zig-nmcli granting NOPASSWD nmcli.
import http.server, subprocess, urllib.parse, html

PORT = 8088
DASHBOARD = "https://web.aquagen.co.in/login"


def nmcli(args, sudo=False, timeout=45):
    cmd = (["sudo", "-n"] if sudo else []) + ["nmcli"] + args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        class R:
            returncode, stdout, stderr = 1, "", str(e)
        return R()


def current():
    r = nmcli(["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    for line in r.stdout.splitlines():
        p = line.split(":")
        if len(p) >= 2 and p[1].startswith("wl"):
            return p[0]
    return "(not connected)"


def scan():
    nmcli(["dev", "wifi", "rescan"])
    r = nmcli(["-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"])
    nets = {}
    for line in r.stdout.splitlines():
        parts = line.rsplit(":", 2)
        if len(parts) != 3:
            continue
        ssid = parts[0].replace("\\:", ":").strip()
        if not ssid:
            continue
        try:
            sig = int(parts[1])
        except ValueError:
            sig = 0
        sec = parts[2] or "open"
        if ssid not in nets or sig > nets[ssid][0]:
            nets[ssid] = (sig, sec)
    return sorted(nets.items(), key=lambda x: -x[1][0])


def bars(sig):
    return "▂▄▆█"[:max(1, min(4, sig // 25 + 1))]


def render(msg="", msg_ok=True):
    cur = html.escape(current())
    rows = ""
    for ssid, (sig, sec) in scan():
        s = html.escape(ssid)
        lock = "🔒" if sec and sec != "open" else ""
        rows += (f'<button type="button" class="net" onclick="pick(this)" data-ssid="{s}">'
                 f'<span class="ss">{s} {lock}</span>'
                 f'<span class="sig">{bars(sig)}</span></button>')
    banner = ""
    if msg:
        color = "#16a34a" if msg_ok else "#dc2626"
        banner = f'<div class="banner" style="background:{color}">{html.escape(msg)}</div>'
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WiFi Setup</title><style>
*{{box-sizing:border-box;font-family:system-ui,Arial,sans-serif}}
body{{margin:0;background:#0f172a;color:#e2e8f0;padding:12px}}
h1{{font-size:20px;margin:4px 0 2px}}
.cur{{font-size:14px;color:#93c5fd;margin-bottom:8px}}
.banner{{color:#fff;padding:8px 10px;border-radius:8px;margin-bottom:8px;font-size:14px}}
.net{{width:100%;display:flex;justify-content:space-between;align-items:center;
  background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:8px;
  padding:12px;margin-bottom:6px;font-size:16px}}
.net.sel{{border-color:#3b82f6;background:#243049}}
.sig{{color:#38bdf8;letter-spacing:2px}}
input,button.act{{width:100%;font-size:16px;padding:12px;border-radius:8px;border:1px solid #334155}}
input{{background:#0b1220;color:#fff;margin:8px 0}}
.act{{background:#3b82f6;color:#fff;border:none;margin-top:6px}}
.row{{display:flex;gap:8px}}.row .act{{flex:1}}
.back{{background:#334155}}
</style></head><body>
<h1>📶 WiFi Setup</h1>
<div class="cur">Connected to: <b>{cur}</b></div>
{banner}
<form method="POST" action="/connect">
  <div id="list">{rows or '<div class="cur">No networks found — tap Rescan.</div>'}</div>
  <input type="hidden" name="ssid" id="ssid">
  <input type="text" name="ssid_manual" placeholder="Or type network name (SSID)">
  <input type="password" name="password" placeholder="Password (leave blank if open)">
  <button class="act" type="submit">Connect</button>
  <div class="row">
    <button class="act back" type="button" onclick="location.href='/'">🔄 Rescan</button>
    <button class="act back" type="button" onclick="location.href='{DASHBOARD}'">← Dashboard</button>
  </div>
</form>
<script>
function pick(b){{
  document.querySelectorAll('.net').forEach(n=>n.classList.remove('sel'));
  b.classList.add('sel');
  document.getElementById('ssid').value=b.dataset.ssid;
  document.querySelector('[name=ssid_manual]').value=b.dataset.ssid;
}}
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        self._send(render())

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        data = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
        ssid = (data.get("ssid_manual", [""])[0] or data.get("ssid", [""])[0]).strip()
        pw = data.get("password", [""])[0]
        if not ssid:
            return self._send(render("Please select or type a network name.", False))
        args = ["dev", "wifi", "connect", ssid]
        if pw:
            args += ["password", pw]
        r = nmcli(args, sudo=True, timeout=60)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0 and "successfully" in out.lower():
            self._send(render(f"Connected to {ssid}.", True))
        else:
            hint = out or "connection failed"
            if "not authorized" in hint.lower() or "password is required" in hint.lower() \
               or "a password is required" in hint.lower():
                hint = "Permission denied — run the one-time sudoers setup for nmcli."
            self._send(render(f"Could not connect to {ssid}: {hint}", False))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
