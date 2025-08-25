import argparse
import json
import socket
import threading
import time
from collections import deque
from typing import Deque, List, Optional

from flask import Flask, Response
from flask_cors import CORS


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
        for _ in range(1, code):
            out.append(src[idx])
            idx += 1
        if code < 0xFF and idx < len(src):
            out.append(0)
    return bytes(out)


def parse_payload(payload: bytes):
    import struct
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
    if len(data) < 2 + 4 * 4:
        return None
    ver = data[0]
    mcount = data[1]
    off = 2
    battery, x, y, theta = struct.unpack_from('<ffff', data, off)
    off += 16

    def read_floats(n):
        nonlocal off
        if n <= 0:
            return []
        vals = list(struct.unpack_from('<' + 'f' * n, data, off))
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


class Broadcaster:
    def __init__(self, maxlen: int = 512):
        self.lock = threading.Lock()
        self.subs: List[Deque[str]] = []
        self.maxlen = maxlen

    def subscribe(self) -> Deque[str]:
        q: Deque[str] = deque(maxlen=self.maxlen)
        with self.lock:
            self.subs.append(q)
        return q

    def unsubscribe(self, q: Deque[str]):
        with self.lock:
            if q in self.subs:
                self.subs.remove(q)

    def publish(self, msg: str):
        with self.lock:
            for q in list(self.subs):
                try:
                    q.append(msg)
                except Exception:
                    pass


class PiTCPReader(threading.Thread):
    def __init__(self, host: str, port: int, pub: Broadcaster, reconnect_delay: float = 1.0):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.pub = pub
        self.reconnect_delay = reconnect_delay
        self.stop_flag = threading.Event()

    def stop(self):
        self.stop_flag.set()

    def run(self):
        buf = bytearray()
        while not self.stop_flag.is_set():
            s: Optional[socket.socket] = None
            try:
                s = socket.create_connection((self.host, self.port), timeout=5.0)
                s.settimeout(2.0)
                # Read loop
                while not self.stop_flag.is_set():
                    try:
                        chunk = s.recv(4096)
                        if not chunk:
                            raise ConnectionError("socket closed")
                        buf.extend(chunk)
                        # Split on 0x00 frame delimiter
                        while True:
                            try:
                                i = buf.index(0)
                            except ValueError:
                                break
                            frame = bytes(buf[:i])
                            del buf[: i + 1]
                            if not frame:
                                continue
                            decoded = cobs_decode(frame)
                            if not decoded:
                                continue
                            pkt = parse_payload(decoded)
                            if pkt is None:
                                continue
                            self.pub.publish(json.dumps(pkt))
                    except socket.timeout:
                        continue
            except Exception:
                time.sleep(self.reconnect_delay)
            finally:
                if s is not None:
                    try:
                        s.close()
                    except Exception:
                        pass


def create_app(pub: Broadcaster) -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.route('/stream')
    def stream():
        q = pub.subscribe()

        def gen():
            try:
                last_ping = time.time()
                while True:
                    if q:
                        msg = q.popleft()
                        yield f"data: {msg}\n\n"
                        last_ping = time.time()
                    else:
                        # keepalive every 10s
                        if time.time() - last_ping > 10:
                            yield ": keepalive\n\n"
                            last_ping = time.time()
                        time.sleep(0.01)
            finally:
                pub.unsubscribe(q)

        return Response(gen(), mimetype='text/event-stream')

    @app.route('/')
    def root():
        return 'OK', 200

    return app


def main():
    ap = argparse.ArgumentParser(description='PC-side SSE proxy for Pi RS-485 TCP bridge')
    ap.add_argument('--pi-host', default='10.0.0.1', help='Pi bridge host (TCP server)')
    ap.add_argument('--pi-port', type=int, default=34453, help='Pi bridge TCP port')
    ap.add_argument('--host', default='127.0.0.1', help='HTTP listen host')
    ap.add_argument('--port', type=int, default=9000, help='HTTP listen port')
    args = ap.parse_args()

    pub = Broadcaster()
    reader = PiTCPReader(args.pi_host, args.pi_port, pub)
    reader.start()

    app = create_app(pub)
    print(f"PC proxy listening on http://{args.host}:{args.port}/stream -> {args.pi_host}:{args.pi_port}")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == '__main__':
    main()

