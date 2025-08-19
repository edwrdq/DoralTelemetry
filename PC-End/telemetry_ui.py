#!/usr/bin/env python3
import socket
import threading
import time
import math
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import json

# Minimal COBS/CRC decode to parse frames from RPi and serve as SSE JSON

def crc16_ccitt(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def cobs_decode(src: bytes) -> bytes:
    if not src:
        return b""
    out = bytearray()
    idx = 0
    while idx < len(src):
        code = src[idx]
        idx += 1
        if code == 0 or idx + code - 1 > len(src) + 0:
            return b""
        for i in range(1, code):
            out.append(src[idx])
            idx += 1
        if code < 0xFF and idx < len(src):
            out.append(0)
    return bytes(out)


def parse_payload(payload: bytes):
    # payload = [data ...][crc_lo][crc_hi]
    if len(payload) < 2:
        return None
    data = payload[:-2]
    crc_lo = payload[-2]
    crc_hi = payload[-1]
    want = ((crc_hi << 8) | crc_lo) & 0xFFFF
    have = crc16_ccitt(data, 0xFFFF)
    if want != have:
        return None
    # unpack
    if len(data) < 2 + 4 * 4:
        return None
    ver = data[0]
    mcount = data[1]
    off = 2
    import struct
    battery, x, y, theta = struct.unpack_from('<ffff', data, off)
    off += 16
    def read_floats(n):
        nonlocal off
        vals = list(struct.unpack_from('<' + 'f'*n, data, off)) if n > 0 else []
        off += 4 * n
        return vals
    temps = read_floats(mcount)
    rpm = read_floats(mcount)
    volts = read_floats(mcount)
    return {
        'version': ver,
        'motorCount': mcount,
        'battery': battery,
        'x': x,
        'y': y,
        'theta': theta,
        'motorTemperature': temps,
        'motorRpm': rpm,
        'motorVoltage': volts,
        'ts': time.time()
    }


class TelemetryProxy:
    def __init__(self, host='10.0.0.1', port=34453):
        self.addr = (host, port)
        self.lock = threading.Lock()
        self.latest = None
        self._stop = False

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._stop = True

    def _run(self):
        while not self._stop:
            try:
                with socket.create_connection(self.addr, timeout=3.0) as s:
                    s.settimeout(1.0)
                    buf = bytearray()
                    while not self._stop:
                        try:
                            chunk = s.recv(4096)
                            if not chunk:
                                break
                            buf.extend(chunk)
                            while True:
                                try:
                                    z = buf.index(0)
                                except ValueError:
                                    break
                                frame = bytes(buf[:z])
                                del buf[:z+1]
                                if not frame:
                                    continue
                                data = cobs_decode(frame)
                                if not data:
                                    continue
                                pkt = parse_payload(data)
                                if pkt:
                                    with self.lock:
                                        self.latest = pkt
                        except socket.timeout:
                            continue
            except Exception:
                time.sleep(0.5)


PROXY = TelemetryProxy()


class Simulator:
    def __init__(self, motor_count: int = 6, hz: int = 200):
        self.motor_count = max(0, int(motor_count))
        self.hz = max(1, int(hz))
        self._stop = False

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._stop = True

    def _run(self):
        t0 = time.time()
        while not self._stop:
            now = time.time() - t0
            battery = 90.0 + 10.0 * math.sin(now * 0.05)
            x = 5.0 * math.sin(now * 0.2)
            y = 5.0 * math.cos(now * 0.2)
            theta = (now * 0.7) % (2 * math.pi)
            temps = [35.0 + 8.0 * math.sin(now * 0.3 + i * 0.25) + random.uniform(-0.3, 0.3)
                     for i in range(self.motor_count)]
            rpm = [220.0 + 60.0 * math.sin(now * 1.1 + i * 0.5) + random.uniform(-3.0, 3.0)
                   for i in range(self.motor_count)]
            volts = [12.0 + 0.8 * math.sin(now * 0.2 + i * 0.15) for i in range(self.motor_count)]
            pkt = {
                'version': 1,
                'motorCount': self.motor_count,
                'battery': battery,
                'x': x,
                'y': y,
                'theta': theta,
                'motorTemperature': temps,
                'motorRpm': rpm,
                'motorVoltage': volts,
                'ts': time.time(),
            }
            with PROXY.lock:
                PROXY.latest = pkt
            time.sleep(1.0 / self.hz)


HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>VEX Telemetry • Gruvbox</title>
  <style>
    :root {
      --bg: #282828; --fg: #ebdbb2; --gray:#a89984; --yellow:#fabd2f; --aqua:#8ec07c; --blue:#83a598; --red:#fb4934;
    }
    * { box-sizing: border-box; }
    html, body { height:100%; margin:0; background:var(--bg); color:var(--fg); font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial; }
    header { padding:12px 16px; border-bottom:1px solid #3c3836; display:flex; justify-content:space-between; align-items:center; }
    h1 { margin:0; font-size:18px; color:var(--yellow); }
    .pill { padding:2px 8px; border-radius:999px; background:#32302f; color:var(--gray); font-size:12px; }
    .ok { color:#b8bb26; } .bad { color:var(--red); }
    .wrap { padding:16px; display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(300px,1fr)); }
    .card { background:#1d2021; border:1px solid #3c3836; border-radius:10px; padding:12px; }
    canvas { width:100%; height:160px; background:#282828; border:1px solid #3c3836; border-radius:6px; }
    .row { display:flex; gap:12px; }
    .k { color:var(--aqua); }
  </style>
  <script>
    function LineChart(canvas, color) {
      const ctx = canvas.getContext('2d');
      const W = canvas.width, H = canvas.height; const N = 512; const data = new Array(N).fill(0); let head = 0;
      function push(v){ data[head] = v; head = (head+1)%N; draw(); }
      function draw(){ ctx.clearRect(0,0,W,H); ctx.strokeStyle=color; ctx.beginPath(); for(let i=0;i<N;i++){ const idx=(head+i)%N; const x=i*(W/N); const y=H- (Math.max(0,Math.min(1,data[idx]))*H); if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);} ctx.stroke(); }
      return { push };
    }
  </script>
</head>
<body>
  <header>
    <h1>VEX Telemetry</h1>
    <div class="pill" id="status">waiting…</div>
  </header>
  <div class="wrap">
    <div class="card">
      <div>Temps (°C)</div>
      <canvas id="t1" width="600" height="160"></canvas>
      <canvas id="t2" width="600" height="160"></canvas>
    </div>
    <div class="card">
      <div>RPM</div>
      <canvas id="r1" width="600" height="160"></canvas>
      <canvas id="r2" width="600" height="160"></canvas>
    </div>
    <div class="card">
      <div class="row"><span class="k">x</span><span id="x">0</span></div>
      <div class="row"><span class="k">y</span><span id="y">0</span></div>
      <div class="row"><span class="k">theta</span><span id="th">0</span></div>
      <div class="row"><span class="k">battery</span><span id="bat">0</span></div>
    </div>
  </div>
  <script>
    const status=document.getElementById('status');
    const xEl=document.getElementById('x'), yEl=document.getElementById('y'), thEl=document.getElementById('th'), batEl=document.getElementById('bat');
    const tc1=LineChart(document.getElementById('t1'),'#fabd2f');
    const tc2=LineChart(document.getElementById('t2'),'#fe8019');
    const rc1=LineChart(document.getElementById('r1'),'#83a598');
    const rc2=LineChart(document.getElementById('r2'),'#8ec07c');
    function connect(){
      const es=new EventSource('/stream');
      es.onopen=()=>{status.textContent='live'; status.classList.add('ok');};
      es.onerror=()=>{status.textContent='disconnected'; status.classList.add('bad');};
      es.onmessage=(e)=>{
        try{ const d=JSON.parse(e.data);
          xEl.textContent=d.x.toFixed(1); yEl.textContent=d.y.toFixed(1); thEl.textContent=d.theta.toFixed(1); batEl.textContent=d.battery.toFixed(0)+'%';
          const m=d.motorCount||0;
          if(m>0){ tc1.push((d.motorTemperature[0]||0)/100); rc1.push((d.motorRpm[0]||0)/600);
                   if(m>1){ tc2.push((d.motorTemperature[1]||0)/100); rc2.push((d.motorRpm[1]||0)/600);} }
        }catch(_){}
      };
    }
    connect();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        if p.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
        elif p.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            last_ts = 0
            try:
                while True:
                    time.sleep(0.005)
                    with PROXY.lock:
                        pkt = PROXY.latest
                    if pkt and pkt.get('ts') != last_ts:
                        last_ts = pkt['ts']
                        self.wfile.write(f"data: {json.dumps(pkt)}\n\n".encode('utf-8'))
            except Exception:
                pass
        else:
            self.send_response(404)
            self.end_headers()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--pi-host', default='10.0.0.1')
    ap.add_argument('--pi-port', type=int, default=34453)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=9000)
    ap.add_argument('--simulate', action='store_true', help='Generate fake telemetry locally (no Pi/robot needed)')
    ap.add_argument('--sim-motors', type=int, default=6, help='Motor count for simulator')
    ap.add_argument('--sim-hz', type=int, default=200, help='Update rate for simulator')
    args = ap.parse_args()

    global PROXY
    PROXY = TelemetryProxy(args.pi_host, args.pi_port)
    if args.simulate:
        sim = Simulator(args.sim_motors, args.sim_hz)
        sim.start()
    else:
        PROXY.start()

    httpd = HTTPServer((args.host, args.port), Handler)
    if args.simulate:
        print(f"UI http://{args.host}:{args.port} • SIMULATING {args.sim_motors} motors @ {args.sim_hz} Hz")
    else:
        print(f"UI http://{args.host}:{args.port} • proxying {args.pi_host}:{args.pi_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
