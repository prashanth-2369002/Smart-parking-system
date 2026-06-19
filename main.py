# main.py — Raspberry Pi Pico W
# Smart Parking System — Chrome Digital Dashboard Edition
#
# Replaces: Blynk app
# Dashboard: open http://<PICO_IP>/ in Chrome after connecting to same WiFi
#
# Wiring (unchanged from your setup):
#   HC-SR04 VCC  → VBUS (5V)      HC-SR04 GND  → GND
#   HC-SR04 TRIG → GP15            HC-SR04 ECHO → voltage divider → GP14
#   IR OUT       → GP13            IR VCC → 3V3   IR GND → GND
#   LED slot1    → GP12 via 220Ω → GND   (ON = occupied)
#   LED slot2    → GP11 via 220Ω → GND   (ON = occupied)
#   Buzzer (+)   → GP10            Buzzer (-) → GND

import time
import network
import socket
from machine import Pin, time_pulse_us

# ─── USER CONFIG ──────────────────────────────────────────────────────────────
WIFI_SSID             = "YOUR_WIFI_SSID"       # <-- change this
WIFI_PASS             = "YOUR_WIFI_PASSWORD"   # <-- change this
ULTRASONIC_THRESHOLD  = 40      # cm — below this = vehicle present (tune this)
UPDATE_INTERVAL_MS    = 500     # sensor read interval
BUZZ_ON_MS            = 200
BUZZ_OFF_MS           = 300

# ─── GPIO ─────────────────────────────────────────────────────────────────────
trig   = Pin(15, Pin.OUT)
echo   = Pin(14, Pin.IN)
ir_pin = Pin(13, Pin.IN)
led1   = Pin(12, Pin.OUT)
led2   = Pin(11, Pin.OUT)
buzzer = Pin(10, Pin.OUT)

led1.value(0); led2.value(0); buzzer.value(0)

# ─── SHARED STATE ─────────────────────────────────────────────────────────────
state = {
    "slot1": {"occupied": False, "distance_cm": -1},
    "slot2": {"occupied": False, "ir": 0},
    "uptime": 0
}

# ─── WIFI ─────────────────────────────────────────────────────────────────────
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print("Connecting to WiFi:", WIFI_SSID)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    t0 = time.time()
    while not wlan.isconnected():
        if time.time() - t0 > 20:
            print("WiFi timeout — running headless")
            break
        time.sleep(0.5)

ip = wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0"
print("IP:", ip)

# ─── SENSOR READS ─────────────────────────────────────────────────────────────
def read_ultrasonic():
    try:
        trig.value(0); time.sleep_us(2)
        trig.value(1); time.sleep_us(10)
        trig.value(0)
        pulse = time_pulse_us(echo, 1, 30000)
        return round(pulse / 58.0, 1) if pulse > 0 else None
    except:
        return None

# ─── HTML DASHBOARD ───────────────────────────────────────────────────────────
# Served as a single self-contained page. All JS, CSS inline.
# Polls /status every second for fresh JSON data.
DASHBOARD_HTML = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Parking Dashboard</title>
<style>
  :root{
    --bg:#080c14;--panel:#0d1421;--border:#1a2540;
    --green:#00ff88;--red:#ff3355;--amber:#ffaa00;
    --text:#cdd6f4;--dim:#6b7a99;--glow-g:0 0 20px #00ff8877;
    --glow-r:0 0 20px #ff335577;--font-mono:'Courier New',monospace;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:system-ui,sans-serif;
    min-height:100vh;padding:20px}

  /* ── Top bar ── */
  .topbar{display:flex;align-items:center;justify-content:space-between;
    margin-bottom:28px;padding-bottom:16px;
    border-bottom:1px solid var(--border)}
  .logo{font-size:22px;font-weight:700;letter-spacing:2px;color:#fff}
  .logo span{color:var(--green)}
  .conn{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--dim)}
  .conn-dot{width:8px;height:8px;border-radius:50%;background:var(--green);
    box-shadow:var(--glow-g);animation:blink 2s ease-in-out infinite}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

  /* ── Summary row ── */
  .summary{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:28px}
  .stat{background:var(--panel);border:1px solid var(--border);border-radius:12px;
    padding:16px 20px;text-align:center}
  .stat-val{font-size:36px;font-weight:800;font-family:var(--font-mono);
    line-height:1;margin-bottom:4px}
  .stat-lbl{font-size:11px;letter-spacing:2px;color:var(--dim);text-transform:uppercase}
  .val-free{color:var(--green);text-shadow:var(--glow-g)}
  .val-occ{color:var(--red);text-shadow:var(--glow-r)}
  .val-total{color:#7aa2f7}

  /* ── Slot cards ── */
  .slots{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:16px;
    padding:24px;position:relative;overflow:hidden;transition:border-color .3s}
  .card.occupied{border-color:var(--red)}
  .card.free{border-color:var(--green)}
  .card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
  .card.occupied::before{background:linear-gradient(90deg,#ff3355,#ff0055)}
  .card.free::before{background:linear-gradient(90deg,#00ff88,#00ccff)}

  .card-header{display:flex;justify-content:space-between;align-items:flex-start;
    margin-bottom:20px}
  .slot-title{font-size:13px;letter-spacing:3px;color:var(--dim);text-transform:uppercase}
  .slot-num{font-size:42px;font-weight:900;color:#fff;line-height:1;
    font-family:var(--font-mono)}

  /* ── Status badge ── */
  .badge{font-size:13px;font-weight:700;letter-spacing:2px;padding:5px 14px;
    border-radius:20px;border:1px solid currentColor;text-transform:uppercase}
  .badge.occ{color:var(--red);background:#ff335512;box-shadow:var(--glow-r)}
  .badge.free{color:var(--green);background:#00ff8812;box-shadow:var(--glow-g)}

  /* ── Pulse ring ── */
  .ring-wrap{display:flex;justify-content:center;margin:20px 0;position:relative}
  .ring{width:100px;height:100px;border-radius:50%;display:flex;
    align-items:center;justify-content:center;position:relative}
  .ring.occ{background:#ff335510;border:2px solid var(--red);
    box-shadow:0 0 30px #ff335540,inset 0 0 20px #ff335520}
  .ring.free{background:#00ff8810;border:2px solid var(--green);
    box-shadow:0 0 30px #00ff8840,inset 0 0 20px #00ff8820}
  .ring .icon{font-size:40px;line-height:1}
  .ring.occ .ripple{position:absolute;border-radius:50%;
    border:2px solid var(--red);animation:ripple 1.8s ease-out infinite;opacity:0}
  .ring.free .ripple{display:none}
  @keyframes ripple{
    0%{width:100px;height:100px;opacity:.7}
    100%{width:180px;height:180px;opacity:0}
  }

  /* ── Distance bar (slot 1 only) ── */
  .dist-section{margin-top:16px}
  .dist-label{font-size:11px;letter-spacing:2px;color:var(--dim);
    text-transform:uppercase;margin-bottom:6px;display:flex;
    justify-content:space-between}
  .dist-val{font-size:22px;font-family:var(--font-mono);font-weight:700;color:#fff}
  .bar-track{height:6px;background:#1a2540;border-radius:3px;
    overflow:hidden;margin-top:8px}
  .bar-fill{height:100%;border-radius:3px;transition:width .5s ease,background .3s}

  /* ── Sensor row ── */
  .sensor-row{display:flex;justify-content:space-between;align-items:center;
    margin-top:16px;padding-top:16px;border-top:1px solid var(--border)}
  .sensor-type{font-size:11px;letter-spacing:2px;color:var(--dim);
    text-transform:uppercase}
  .sensor-val{font-size:13px;font-family:var(--font-mono);color:var(--amber)}

  /* ── Footer ── */
  .footer{margin-top:28px;text-align:center;font-size:12px;color:var(--dim);
    letter-spacing:1px}
  .uptime{font-family:var(--font-mono);color:var(--text)}

  /* ── Error state ── */
  .conn-dot.err{background:var(--red);animation:none;box-shadow:var(--glow-r)}

  @media(max-width:480px){
    .summary{grid-template-columns:repeat(3,1fr)}
    .stat-val{font-size:28px}
  }
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">SMART<span>PARK</span></div>
  <div class="conn">
    <div class="conn-dot" id="conn-dot"></div>
    <span id="conn-txt">Live</span>
  </div>
</div>

<div class="summary">
  <div class="stat">
    <div class="stat-val val-free" id="s-free">–</div>
    <div class="stat-lbl">Free Slots</div>
  </div>
  <div class="stat">
    <div class="stat-val val-occ" id="s-occ">–</div>
    <div class="stat-lbl">Occupied</div>
  </div>
  <div class="stat">
    <div class="stat-val val-total">2</div>
    <div class="stat-lbl">Total Slots</div>
  </div>
</div>

<div class="slots">

  <!-- Slot 1 — Ultrasonic -->
  <div class="card" id="card1">
    <div class="card-header">
      <div>
        <div class="slot-title">Slot</div>
        <div class="slot-num">01</div>
      </div>
      <span class="badge" id="badge1">–</span>
    </div>

    <div class="ring-wrap">
      <div class="ring" id="ring1">
        <div class="ripple"></div>
        <span class="icon" id="icon1">🔲</span>
      </div>
    </div>

    <div class="dist-section">
      <div class="dist-label">
        <span>Distance</span>
        <span class="dist-val" id="dist-val">– cm</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" id="dist-bar" style="width:0%;background:var(--green)"></div>
      </div>
    </div>

    <div class="sensor-row">
      <span class="sensor-type">Ultrasonic HC-SR04</span>
      <span class="sensor-val" id="s1-raw">–</span>
    </div>
  </div>

  <!-- Slot 2 — IR -->
  <div class="card" id="card2">
    <div class="card-header">
      <div>
        <div class="slot-title">Slot</div>
        <div class="slot-num">02</div>
      </div>
      <span class="badge" id="badge2">–</span>
    </div>

    <div class="ring-wrap">
      <div class="ring" id="ring2">
        <div class="ripple"></div>
        <span class="icon" id="icon2">🔲</span>
      </div>
    </div>

    <div class="sensor-row" style="margin-top:auto;padding-top:16px;border-top:1px solid var(--border)">
      <span class="sensor-type">IR Proximity Sensor</span>
      <span class="sensor-val" id="s2-raw">–</span>
    </div>
  </div>

</div>

<div class="footer">
  Pico W · MicroPython · Auto-refresh 1s &nbsp;|&nbsp;
  Uptime <span class="uptime" id="uptime">–</span>
</div>

<script>
const dot = document.getElementById('conn-dot');
const connTxt = document.getElementById('conn-txt');

function setSlot(n, occupied, extraInfo) {
  const card  = document.getElementById('card' + n);
  const badge = document.getElementById('badge' + n);
  const ring  = document.getElementById('ring' + n);
  const icon  = document.getElementById('icon' + n);

  card.className  = 'card ' + (occupied ? 'occupied' : 'free');
  badge.className = 'badge ' + (occupied ? 'occ' : 'free');
  badge.textContent = occupied ? 'Occupied' : 'Free';
  ring.className  = 'ring ' + (occupied ? 'occ' : 'free');
  icon.textContent = occupied ? '🚗' : '✅';
}

function fmtUptime(s) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return (h ? h + 'h ' : '') + (m ? m + 'm ' : '') + ss + 's';
}

async function refresh() {
  try {
    const r = await fetch('/status', { signal: AbortSignal.timeout(2000) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();

    // Connection indicator
    dot.className = 'conn-dot';
    connTxt.textContent = 'Live';

    // Slot 1
    const occ1 = d.slot1 && (d.slot1.occupied === true || d.slot1.occupied === 'true');
    setSlot(1, occ1);
    const dist = d.slot1 && d.slot1.distance_cm;
    if (dist !== undefined && dist > 0) {
      document.getElementById('dist-val').textContent = dist + ' cm';
      document.getElementById('s1-raw').textContent = dist + ' cm';
      // Fill bar: 0 cm = 100% fill (vehicle right at sensor), 100+ cm = 0%
      const pct = Math.max(0, Math.min(100, 100 - (dist / 100 * 100)));
      const bar = document.getElementById('dist-bar');
      bar.style.width = pct + '%';
      bar.style.background = occ1 ? 'var(--red)' : 'var(--green)';
    } else {
      document.getElementById('dist-val').textContent = '— cm';
      document.getElementById('s1-raw').textContent = 'timeout';
    }

    // Slot 2
    const occ2 = d.slot2 && (d.slot2.occupied === true || d.slot2.occupied === 'true');
    setSlot(2, occ2);
    const ir = d.slot2 && d.slot2.ir !== undefined ? d.slot2.ir : '–';
    document.getElementById('s2-raw').textContent = 'IR=' + ir;

    // Summary
    const free = [!occ1, !occ2].filter(Boolean).length;
    const occ  = 2 - free;
    document.getElementById('s-free').textContent = free;
    document.getElementById('s-occ').textContent  = occ;

    // Uptime
    if (d.uptime !== undefined) {
      document.getElementById('uptime').textContent = fmtUptime(d.uptime);
    }

  } catch (e) {
    dot.className = 'conn-dot err';
    connTxt.textContent = 'Reconnecting…';
  }
}

refresh();
setInterval(refresh, 1000);
</script>
</body>
</html>
"""

# ─── HTTP SERVER ──────────────────────────────────────────────────────────────
def make_server(port=80):
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    s.settimeout(0.05)      # non-blocking so sensor loop keeps running
    print("Dashboard → http://{}/ (open in Chrome)".format(ip))
    return s

def handle_request(cl):
    try:
        f = cl.makefile("rwb", 0)
        line = f.readline()
        while f.readline() not in (b"\r\n", b""):
            pass
        if not line:
            return
        path = line.decode().split()[1] if len(line.decode().split()) > 1 else "/"

        if path.startswith("/status"):
            import ujson
            body = ujson.dumps(state)
            cl.send(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n"
                    b"Cache-Control: no-cache\r\nConnection: close\r\n\r\n")
            cl.send(body)
        else:
            cl.send(b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                    b"Connection: close\r\n\r\n")
            cl.send(DASHBOARD_HTML)
    except Exception as e:
        try:
            cl.send(b"HTTP/1.0 500\r\n\r\n")
        except:
            pass
    finally:
        try:
            cl.close()
        except:
            pass

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────
def main():
    server = make_server()

    last_sensor  = 0
    last_buzz    = 0
    buzz_state   = 0
    boot_time    = time.time()

    while True:
        now = time.ticks_ms()

        # ── Sensor reads ──────────────────────────────────────────────────────
        if time.ticks_diff(now, last_sensor) >= UPDATE_INTERVAL_MS:
            last_sensor = now

            dist = read_ultrasonic()
            occ1 = dist is not None and dist < ULTRASONIC_THRESHOLD

            irv  = 1 - ir_pin.value()   # invert: active-low IR
            occ2 = irv == 1

            led1.value(1 if occ1 else 0)
            led2.value(1 if occ2 else 0)

            state["slot1"]["occupied"]    = occ1
            state["slot1"]["distance_cm"] = dist if dist is not None else -1
            state["slot2"]["occupied"]    = occ2
            state["slot2"]["ir"]          = int(irv)
            state["uptime"]               = time.time() - boot_time

            # ── Buzzer: beep when any slot occupied ───────────────────────────
            if occ1 or occ2:
                if buzz_state == 0:
                    buzzer.value(1)
                    buzz_state = 1
                    last_buzz  = now
                elif time.ticks_diff(now, last_buzz) >= BUZZ_ON_MS:
                    buzzer.value(0)
                    buzz_state = 0
                    last_buzz  = now
            else:
                buzzer.value(0)
                buzz_state = 0

        # ── HTTP request ──────────────────────────────────────────────────────
        try:
            cl, _ = server.accept()
            handle_request(cl)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped")
