#!/usr/bin/env python3
# Tiny WiFi manager for the kiosk. Opened by the WiFi icon on the AquaGen page.
# Scans networks and connects via nmcli. Has a built-in on-screen keyboard so
# the SSID/password can be typed on the touchscreen. Sized for the 7" screen.
# Connecting needs /etc/sudoers.d/zig-nmcli granting NOPASSWD nmcli.
import http.server, subprocess, urllib.parse, html, threading

PORT = 8088
DASHBOARD = "https://web.aquagen.co.in/login"


def exit_to_desktop():
    # Close the kiosk browser so the Raspberry Pi desktop shows. A short delay
    # lets the HTTP response reach the browser before it is killed.
    def _kill():
        subprocess.run(["pkill", "-x", "chromium"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    threading.Timer(1.0, _kill).start()


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


def scan(force=False):
    if force:
        # A real rescan needs privileges; try sudo, ignore failure.
        nmcli(["dev", "wifi", "rescan"], sudo=True, timeout=25)
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


KEYBOARD_JS = r"""
(function(){
  var target=null, shift=false;
  var rows=["1234567890","qwertyuiop","asdfghjkl","zxcvbnm"];
  var kb=document.getElementById('kb');
  function mk(t,fn,cls){var b=document.createElement('button');b.type='button';
    b.className='kbk'+(cls?' '+cls:'');b.textContent=t;
    b.addEventListener('mousedown',function(e){e.preventDefault();fn();});
    b.addEventListener('touchstart',function(e){e.preventDefault();fn();},{passive:false});
    return b;}
  function ins(c){if(!target)return;var s=target.selectionStart;if(s==null)s=target.value.length;
    var e=target.selectionEnd;if(e==null)e=s;
    target.value=target.value.slice(0,s)+c+target.value.slice(e);
    target.selectionStart=target.selectionEnd=s+c.length;}
  function bksp(){if(!target)return;var s=target.selectionStart;if(s==null)s=target.value.length;
    var e=target.selectionEnd;if(e==null)e=s;
    if(s===e&&s>0){target.value=target.value.slice(0,s-1)+target.value.slice(e);
      target.selectionStart=target.selectionEnd=s-1;}
    else{target.value=target.value.slice(0,s)+target.value.slice(e);
      target.selectionStart=target.selectionEnd=s;}}
  function build(){
    kb.innerHTML='';
    rows.forEach(function(r){var d=document.createElement('div');d.className='kbrow';
      r.split('').forEach(function(c){var ch=shift?c.toUpperCase():c;d.appendChild(mk(ch,function(){ins(ch);}));});
      kb.appendChild(d);});
    var d2=document.createElement('div');d2.className='kbrow';
    "@._-#!".split('').forEach(function(c){d2.appendChild(mk(c,function(){ins(c);}));});
    d2.appendChild(mk(shift?'⇪':'⇧',function(){shift=!shift;build();}));
    kb.appendChild(d2);
    var d3=document.createElement('div');d3.className='kbrow';
    d3.appendChild(mk('space',function(){ins(' ');},'wide'));
    d3.appendChild(mk('⌫',function(){bksp();},'wide'));
    d3.appendChild(mk('Done',function(){kb.classList.remove('show');},'wide'));
    kb.appendChild(d3);
  }
  document.addEventListener('focusin',function(e){
    if(e.target.tagName==='INPUT'&&e.target.type!=='hidden'){target=e.target;kb.classList.add('show');}});
  build();
})();
"""


def render(msg="", msg_ok=True):
    cur = html.escape(current())
    rows = ""
    for ssid, (sig, sec) in scan():
        s = html.escape(ssid)
        lock = "\U0001f512" if sec and sec != "open" else ""
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
body{{margin:0;background:#0f172a;color:#e2e8f0;padding:10px 10px 240px}}
h1{{font-size:19px;margin:2px 0}}
.cur{{font-size:13px;color:#93c5fd;margin-bottom:6px}}
.banner{{color:#fff;padding:8px 10px;border-radius:8px;margin-bottom:8px;font-size:14px}}
.net{{width:100%;display:flex;justify-content:space-between;align-items:center;
  background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:8px;
  padding:11px;margin-bottom:5px;font-size:15px}}
.net.sel{{border-color:#3b82f6;background:#243049}}
.sig{{color:#38bdf8;letter-spacing:2px}}
input,.act{{width:100%;font-size:16px;padding:11px;border-radius:8px;border:1px solid #334155}}
input{{background:#0b1220;color:#fff;margin:7px 0}}
.act{{background:#3b82f6;color:#fff;border:none;margin-top:6px}}
.row{{display:flex;gap:8px}}.row .act{{flex:1}}
.back{{background:#334155}}
#kb{{position:fixed;left:0;right:0;bottom:0;background:#111827;padding:4px;display:none;z-index:1000;
  box-shadow:0 -2px 10px rgba(0,0,0,.5)}}
#kb.show{{display:block}}
.kbrow{{display:flex;justify-content:center;gap:3px;margin:3px 0}}
.kbk{{flex:1;max-width:46px;height:40px;background:#334155;color:#fff;border:none;border-radius:6px;
  font-size:16px}}
.kbk.wide{{max-width:110px}}.kbk:active{{background:#3b82f6}}
</style></head><body>
<h1>\U0001f4f6 WiFi Setup</h1>
<div class="cur">Connected to: <b>{cur}</b></div>
{banner}
<form method="POST" action="/connect">
  <div id="list">{rows or '<div class="cur">No networks found - tap Rescan.</div>'}</div>
  <input type="hidden" name="ssid" id="ssid">
  <input type="text" name="ssid_manual" placeholder="Network name (SSID)" autocomplete="off">
  <input type="password" name="password" placeholder="Password (blank if open)" autocomplete="off">
  <button class="act" type="submit">Connect</button>
  <div class="row">
    <button class="act back" type="button" onclick="location.href='/rescan'">\U0001f504 Rescan</button>
    <button class="act back" type="button" onclick="location.href='{DASHBOARD}'">← Dashboard</button>
    <button class="act back" type="button" onclick="location.href='/desktop'">\U0001f3e0 Home</button>
  </div>
</form>
<div id="kb"></div>
<script>
function pick(b){{document.querySelectorAll('.net').forEach(function(n){{n.classList.remove('sel');}});
  b.classList.add('sel');document.getElementById('ssid').value=b.dataset.ssid;
  document.querySelector('[name=ssid_manual]').value=b.dataset.ssid;}}
{KEYBOARD_JS}
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        if self.path.startswith("/rescan"):
            scan(force=True)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        if self.path.startswith("/desktop"):
            self._send("<!doctype html><meta charset='utf-8'><body "
                       "style='background:#0f172a;color:#e2e8f0;font-family:sans-serif;"
                       "padding:24px'><h2>Exiting to the desktop…</h2>"
                       "<p>To return to the dashboard, double-click the "
                       "<b>AquaGen Kiosk</b> icon on the desktop, or reboot.</p></body>")
            exit_to_desktop()
            return
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
            low = hint.lower()
            if "not authorized" in low or "password is required" in low:
                hint = "Permission denied - run the one-time nmcli sudoers setup."
            self._send(render(f"Could not connect to {ssid}: {hint}", False))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
