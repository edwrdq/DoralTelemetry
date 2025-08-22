import struct
import time
import random
import json
from flask import Flask, Response
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
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

def make_payload(motor_count=4):
    version = 1
    battery = random.uniform(80, 100)
    x = random.uniform(0, 144)
    y = random.uniform(0, 144)
    theta = random.uniform(0, 360)
    temps = [random.uniform(30, 55) for _ in range(motor_count)]
    rpm = [random.uniform(0, 600) for _ in range(motor_count)]
    volts = [random.uniform(11, 13) for _ in range(motor_count)]
    payload = struct.pack('<BBffff', version, motor_count, battery, x, y, theta)
    for arr in (temps, rpm, volts):
        payload += struct.pack('<' + 'f'*motor_count, *arr)
    crc = crc16_ccitt(payload)
    payload += struct.pack('<H', crc)
    return payload

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
    if len(data) < 2 + 4 * 4:
        return None
    ver = data[0]
    mcount = data[1]
    off = 2
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

import json

def telemetry_generator(motor_count=4, hz=200):
    while True:
        payload = make_payload(motor_count)
        pkt = parse_payload(payload)
        if pkt:
            yield f"data: {json.dumps(pkt)}\n\n"
        time.sleep(1.0 / hz)

@app.route("/stream")
def stream():
    from flask import request
    motors = int(request.args.get("motors", 4))
    hz = int(request.args.get("hz", 200))
    return Response(telemetry_generator(motors, hz), mimetype="text/event-stream")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=34453)
    ap.add_argument('--motors', type=int, default=4)
    ap.add_argument('--hz', type=int, default=200)
    args = ap.parse_args()
    print(f"Mock RPi SSE server listening on http://{args.host}:{args.port}/stream (motors={args.motors}, {args.hz}Hz)")
    app.run(host=args.host, port=args.port, threaded=True)
