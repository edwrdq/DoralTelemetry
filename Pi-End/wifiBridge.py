# Requirements:
#   uv pip install pyserial gpiozero flask

import serial
import struct
import time
import json
from gpiozero import DigitalOutputDevice
from flask import Flask, Response
import threading

"""
RS485 -> TCP Bridge
-------------------
GPIO 14(TX) -> MAX485 DI
GPIO 15(RX) -> MAX485 RO
GPIO 17 -> MAX485 DE/RE (low for receive, high for transmit)

Now decodes COBS+CRC16 frames from UART, parses payload, and sends JSON lines (newline-delimited) via TCP SSE.
"""

#----- RS-485 (UART) Configuration -----
UART_DEV = '/dev/serial0'  # UART device
BAUD = 512_000
ser485 = serial.Serial(UART_DEV, BAUD, timeout=0.02)

dir_pin = DigitalOutputDevice(17, active_high=True, initial_value=False)

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

# Flask SSE server
app = Flask(__name__)

def uart_stream():
    buf = bytearray()
    while True:
        data = ser485.read(1024)
        if not data:
            time.sleep(0.005)
            continue
        buf.extend(data)
        while True:
            try:
                z = buf.index(0)
            except ValueError:
                break
            frame = bytes(buf[:z])
            del buf[:z+1]
            if not frame:
                continue
            decoded = cobs_decode(frame)
            if not decoded:
                continue
            pkt = parse_payload(decoded)
            if pkt:
                yield f"data: {json.dumps(pkt)}\n\n"

@app.route("/stream")
def stream():
    return Response(uart_stream(), mimetype="text/event-stream")

@app.route("/")
def index():
    return "<h1>VEX Telemetry Pi Bridge</h1><p>Visit <code>/stream</code> for SSE JSON.</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=34453, threaded=True)

