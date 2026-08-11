#!/usr/bin/env python3
# Interactive WiFi manager for the kiosk. Opened by the WiFi icon on the AquaGen
# page. Single page + JSON API (live scan/connect, no full reloads), signal
# bars, show-password toggle, built-in on-screen keyboard, and a Home button.
# Connecting needs /etc/sudoers.d/zig-nmcli granting NOPASSWD nmcli.
import http.server, subprocess, json, html

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


def status():
    name = ""
    r = nmcli(["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    for line in r.stdout.splitlines():
        p = line.split(":")
        if len(p) >= 2 and p[1].startswith("wl"):
            name = p[0]
    ip = ""
    r2 = nmcli(["-t", "-f", "IP4.ADDRESS", "device", "show", "wlan0"])
    for line in r2.stdout.splitlines():
        if line.startswith("IP4.ADDRESS") and ":" in line:
            ip = line.split(":", 1)[1].split("/")[0]
            break
    return {"connected": bool(name), "name": name or "(not connected)", "ip": ip}


def scan(force=False):
    if force:
        nmcli(["dev", "wifi", "rescan"], sudo=True, timeout=25)
    r = nmcli(["-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"])
    nets = {}
    for line in r.stdout.splitlines():
        parts = line.rsplit(":", 3)
        if len(parts) != 4:
            continue
        inuse, ssid, signal, sec = parts
        ssid = ssid.replace("\\:", ":").strip()
        if not ssid:
            continue
        try:
            sig = int(signal)
        except ValueError:
            sig = 0
        cur = inuse.strip() == "*"
        if ssid not in nets or sig > nets[ssid]["signal"]:
            nets[ssid] = {"ssid": ssid, "signal": sig,
                          "secure": bool(sec and sec != "open"), "current": cur}
    return sorted(nets.values(), key=lambda n: (-n["current"], -n["signal"]))


def connect(ssid, password):
    if not ssid:
        return {"ok": False, "message": "Please select or type a network name."}
    args = ["dev", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    r = nmcli(args, sudo=True, timeout=60)
    out = (r.stdout + r.stderr).strip()
    low = out.lower()
    if r.returncode == 0 and "successfully" in low:
        return {"ok": True, "message": f"Connected to {ssid}."}
    if "not authorized" in low or "password is required" in low:
        return {"ok": False, "message": "Permission denied — run the one-time "
                "nmcli sudoers setup (sudo bash setup-wifi-sudo.sh)."}
    return {"ok": False, "message": out or "Connection failed."}


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WiFi Setup</title><style>
*{box-sizing:border-box;font-family:system-ui,Arial,sans-serif;-webkit-tap-highlight-color:transparent}
body{margin:0;background:#0f172a;color:#e2e8f0;padding:10px 10px 250px}
.head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.head h1{font-size:19px;margin:0}
.status{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:10px 12px;margin-bottom:10px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.on{background:#22c55e;box-shadow:0 0 6px #22c55e}.off{background:#ef4444}
.sub{font-size:12px;color:#94a3b8;margin-top:2px}
.banner{color:#fff;padding:9px 12px;border-radius:9px;margin-bottom:9px;font-size:14px;display:none}
.net{width:100%;display:flex;justify-content:space-between;align-items:center;
  background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:10px;
  padding:12px;margin-bottom:6px;font-size:15px;transition:background .15s,border-color .15s}
.net.sel{border-color:#3b82f6;background:#243049}
.net .r{display:flex;align-items:center;gap:8px}
.bars{display:inline-flex;align-items:flex-end;gap:2px;height:16px}
.bars i{width:4px;background:#475569;border-radius:1px}
.bars i.a{background:#38bdf8}
.lock{opacity:.7}
input{width:100%;font-size:16px;padding:12px;border-radius:9px;border:1px solid #334155;
  background:#0b1220;color:#fff;margin:7px 0}
.pw{position:relative}.pw input{padding-right:52px}
.eye{position:absolute;right:6px;top:50%;transform:translateY(-50%);background:#334155;
  border:none;color:#fff;border-radius:7px;padding:8px 10px;font-size:13px}
.act{width:100%;font-size:16px;padding:12px;border-radius:9px;border:none;background:#3b82f6;
  color:#fff;margin-top:6px;transition:opacity .15s}
.act[disabled]{opacity:.55}
.row{display:flex;gap:8px}.row .act{flex:1;background:#334155}
.spin{display:none;width:16px;height:16px;border:3px solid #ffffff55;border-top-color:#fff;
  border-radius:50%;animation:sp .7s linear infinite;vertical-align:-3px;margin-right:6px}
@keyframes sp{to{transform:rotate(360deg)}}
.muted{color:#94a3b8;font-size:13px;text-align:center;padding:12px}
#kb{position:fixed;left:0;right:0;bottom:0;background:#111827;padding:4px;display:none;z-index:1000;
  box-shadow:0 -2px 10px rgba(0,0,0,.5)}
#kb.show{display:block}
.kbrow{display:flex;justify-content:center;gap:3px;margin:3px 0}
.kbk{flex:1;max-width:46px;height:40px;background:#334155;color:#fff;border:none;border-radius:6px;font-size:16px}
.kbk.wide{max-width:110px}.kbk:active{background:#3b82f6}
</style></head><body>
<div class="head"><span style="font-size:22px">\U0001f4f6</span><h1>WiFi Setup</h1></div>
<div class="status" id="status"><span class="dot off"></span>Loading…</div>
<div class="banner" id="banner"></div>
<div id="list"><div class="muted">Scanning for networks…</div></div>
<input type="text" id="ssid" placeholder="Network name (SSID)" autocomplete="off">
<div class="pw"><input type="password" id="password" placeholder="Password (blank if open)" autocomplete="off">
  <button class="eye" type="button" id="eye">show</button></div>
<button class="act" id="connect"><span class="spin" id="cspin"></span>Connect</button>
<div class="row">
  <button class="act" id="rescan"><span class="spin" id="rspin"></span>\U0001f504 Rescan</button>
  <button class="act" onclick="location.href='DASH'">← Dashboard</button>
  <button class="act" onclick="location.href='/desktop'">\U0001f3e0 Home</button>
</div>
<div id="kb"></div>
<script>
var $=function(id){return document.getElementById(id)};
function bars(sig){var n=Math.max(1,Math.min(4,Math.round(sig/25)));var h='';
  for(var i=1;i<=4;i++){h+='<i class="'+(i<=n?'a':'')+'" style="height:'+(i*4)+'px"></i>'}return '<span class="bars">'+h+'</span>'}
function banner(msg,ok){var b=$('banner');b.textContent=msg;b.style.display='block';
  b.style.background=ok?'#16a34a':'#dc2626'}
function loadStatus(){fetch('/api/status').then(r=>r.json()).then(function(s){
  $('status').innerHTML='<span class="dot '+(s.connected?'on':'off')+'"></span><b>'+
   (s.connected?'Connected':'Not connected')+'</b> — '+s.name+
   (s.ip?'<div class="sub">IP: '+s.ip+'</div>':'')})}
function render(nets){var l=$('list');if(!nets.length){l.innerHTML='<div class="muted">No networks found — tap Rescan.</div>';return}
  l.innerHTML='';nets.forEach(function(n){var d=document.createElement('button');d.type='button';d.className='net'+(n.current?' sel':'');
    d.innerHTML='<span class="r">'+bars(n.signal)+' '+esc(n.ssid)+'</span><span>'+(n.secure?'<span class="lock">\U0001f512</span>':'')+(n.current?' ✓':'')+'</span>';
    d.onclick=function(){document.querySelectorAll('.net').forEach(x=>x.classList.remove('sel'));d.classList.add('sel');
      $('ssid').value=n.ssid;var p=$('password');p.focus();showKb(p)};l.appendChild(d)})}
function esc(s){var e=document.createElement('span');e.textContent=s;return e.innerHTML}
function loadScan(force){var sp=$('rspin');if(force)sp.style.display='inline-block';$('rescan').disabled=true;
  fetch('/api/scan'+(force?'?force=1':'')).then(r=>r.json()).then(function(d){render(d.networks);
    sp.style.display='none';$('rescan').disabled=false}).catch(function(){sp.style.display='none';$('rescan').disabled=false})}
$('connect').onclick=function(){var ssid=$('ssid').value.trim(),pw=$('password').value;
  if(!ssid){banner('Select or type a network name.',false);return}
  $('cspin').style.display='inline-block';this.disabled=true;banner('Connecting to '+ssid+'…',true);
  fetch('/api/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:ssid,password:pw})})
   .then(r=>r.json()).then(function(res){$('cspin').style.display='none';$('connect').disabled=false;
    banner(res.message,res.ok);loadStatus();if(res.ok)loadScan(false)})
   .catch(function(){$('cspin').style.display='none';$('connect').disabled=false;banner('Connection error.',false)})};
$('rescan').onclick=function(){loadScan(true)};
$('eye').onclick=function(){var p=$('password');if(p.type==='password'){p.type='text';this.textContent='hide'}else{p.type='password';this.textContent='show'}};
// on-screen keyboard
var kbTarget=null,shift=false,kb=$('kb');
function showKb(t){kbTarget=t;kb.classList.add('show')}
function mk(t,fn,cls){var b=document.createElement('button');b.type='button';b.className='kbk'+(cls?' '+cls:'');b.textContent=t;
  b.addEventListener('mousedown',function(e){e.preventDefault();fn()});
  b.addEventListener('touchstart',function(e){e.preventDefault();fn()},{passive:false});return b}
function ins(c){if(!kbTarget)return;var s=kbTarget.selectionStart;if(s==null)s=kbTarget.value.length;var e=kbTarget.selectionEnd;if(e==null)e=s;
  kbTarget.value=kbTarget.value.slice(0,s)+c+kbTarget.value.slice(e);kbTarget.selectionStart=kbTarget.selectionEnd=s+c.length}
function bksp(){if(!kbTarget)return;var s=kbTarget.selectionStart;if(s==null)s=kbTarget.value.length;var e=kbTarget.selectionEnd;if(e==null)e=s;
  if(s===e&&s>0){kbTarget.value=kbTarget.value.slice(0,s-1)+kbTarget.value.slice(e);kbTarget.selectionStart=kbTarget.selectionEnd=s-1}
  else{kbTarget.value=kbTarget.value.slice(0,s)+kbTarget.value.slice(e);kbTarget.selectionStart=kbTarget.selectionEnd=s}}
function buildKb(){kb.innerHTML='';['1234567890','qwertyuiop','asdfghjkl','zxcvbnm'].forEach(function(r){
  var d=document.createElement('div');d.className='kbrow';r.split('').forEach(function(c){var ch=shift?c.toUpperCase():c;d.appendChild(mk(ch,function(){ins(ch)}))});kb.appendChild(d)});
  var d2=document.createElement('div');d2.className='kbrow';'@._-#!'.split('').forEach(function(c){d2.appendChild(mk(c,function(){ins(c)}))});
  d2.appendChild(mk(shift?'⇪':'⇧',function(){shift=!shift;buildKb()}));kb.appendChild(d2);
  var d3=document.createElement('div');d3.className='kbrow';d3.appendChild(mk('space',function(){ins(' ')},'wide'));
  d3.appendChild(mk('⌫',function(){bksp()},'wide'));d3.appendChild(mk('Done',function(){kb.classList.remove('show')},'wide'));kb.appendChild(d3)}
document.addEventListener('focusin',function(e){if(e.target.tagName==='INPUT'&&e.target.type!=='hidden')showKb(e.target)});
buildKb();loadStatus();loadScan(false);
</script></body></html>""".replace("DASH", DASHBOARD)


class Handler(http.server.BaseHTTPRequestHandler):
    def _json(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b)

    def _html(self, s):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(s.encode("utf-8"))

    def do_GET(self):
        if self.path.startswith("/api/status"):
            return self._json(status())
        if self.path.startswith("/api/scan"):
            return self._json({"networks": scan(force="force=1" in self.path)})
        if self.path.startswith("/desktop"):
            self._html("<!doctype html><meta charset='utf-8'><body style='background:#0f172a;"
                       "color:#e2e8f0;font-family:sans-serif;padding:24px'><h2>Exiting to the "
                       "desktop…</h2><p>Return via the <b>AquaGen Kiosk</b> desktop icon, or "
                       "reboot.</p></body>")
            import threading
            threading.Timer(1.0, lambda: subprocess.run(
                ["pkill", "-x", "chromium"], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)).start()
            return
        self._html(PAGE)

    def do_POST(self):
        if self.path.startswith("/api/connect"):
            n = int(self.headers.get("Content-Length", 0))
            try:
                data = json.loads(self.rfile.read(n).decode("utf-8"))
            except Exception:
                data = {}
            return self._json(connect(data.get("ssid", "").strip(), data.get("password", "")))
        self.send_response(404)
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
