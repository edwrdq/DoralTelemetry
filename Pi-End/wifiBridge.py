"""
Requirements (Pi):
  pip3 install pyserial gpiozero

RS‑485 → TCP Bridge (raw bytes)
--------------------------------
GPIO 14(TX) -> MAX485 DI
GPIO 15(RX) -> MAX485 RO
GPIO 17 -> MAX485 DE/RE (low for receive, high for transmit)

Reads raw COBS+CRC16 framed bytes from UART and forwards them
unchanged over a TCP socket to all connected clients. Frames are
delimited by 0x00 on the wire. This aligns with PC-End `pc_proxy.py`.

Mock mode is available with `--mock` to generate realistic frames
without hardware; frames are still raw TCP (COBS+CRC16, 0x00-delimited).
"""

import argparse
import math
import random
import socket
import struct
import threading
import time
from typing import Optional

import serial
from gpiozero import DigitalOutputDevice


class ClientPool:
    def __init__(self):
        self.lock = threading.Lock()
        self.clients: list[socket.socket] = []

    def add(self, s: socket.socket):
        s.setblocking(False)
        with self.lock:
            self.clients.append(s)

    def remove(self, s: socket.socket):
        with self.lock:
            if s in self.clients:
                self.clients.remove(s)
        try:
            s.close()
        except Exception:
            pass

    def broadcast(self, data: bytes):
        if not data:
            return
        with self.lock:
            dead: list[socket.socket] = []
            for c in self.clients:
                try:
                    c.sendall(data)
                except Exception:
                    dead.append(c)
            for c in dead:
                try:
                    self.clients.remove(c)
                except ValueError:
                    pass
                try:
                    c.close()
                except Exception:
                    pass


def uart_reader(ser: serial.Serial, pool: ClientPool, stop: threading.Event):
    while not stop.is_set():
        try:
            chunk = ser.read(1024)
            if chunk:
                # Forward raw bytes (COBS frames delimited with 0x00)
                pool.broadcast(chunk)
            else:
                time.sleep(0.002)
        except Exception:
            time.sleep(0.01)


def tcp_server(host: str, port: int, pool: ClientPool, stop: threading.Event):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    srv.settimeout(1.0)
    print(f"Pi bridge listening on {host}:{port} (raw TCP, COBS+CRC16, 0x00-delimited)")
    try:
        while not stop.is_set():
            try:
                conn, addr = srv.accept()
                print(f"Client connected: {addr}")
                pool.add(conn)
            except socket.timeout:
                continue
            except Exception:
                time.sleep(0.1)
    finally:
        try:
            srv.close()
        except Exception:
            pass


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


def cobs_encode(src: bytes) -> bytes:
    if not src:
        return b"\x01\x00"
    out = bytearray()
    code_index = 0
    out.append(0)  # placeholder for code
    code = 1
    for b in src:
        if b == 0:
            out[code_index] = code
            code_index = len(out)
            out.append(0)  # new code placeholder
            code = 1
        else:
            out.append(b)
            code += 1
            if code == 0xFF:
                out[code_index] = 0xFF
                code_index = len(out)
                out.append(0)
                code = 1
    out[code_index] = code
    out.append(0)  # delimiter
    return bytes(out)


class RobotSim:
    def __init__(self, motor_count: int = 4):
        self.x = random.uniform(-36, 36)
        self.y = random.uniform(-36, 36)
        self.theta = random.uniform(0, 360)
        self.v = 0.0
        self.omega = 0.0
        self.last_update = time.time()
        self.battery = random.uniform(80, 100)
        self.motor_count = motor_count
        self.temps = [random.uniform(30, 55) for _ in range(self.motor_count)]
        self.rpm = [random.uniform(0, 600) for _ in range(self.motor_count)]
        self.volts = [random.uniform(11, 13) for _ in range(self.motor_count)]
        self.waypoint = self._random_waypoint()
        self.reached_threshold = 2.0
        self.max_speed = 3.0
        self.max_turn = 90.0

    def _random_waypoint(self):
        return (random.uniform(-60, 60), random.uniform(-60, 60))

    def step(self, dt):
        dt = dt * 10
        dx = self.waypoint[0] - self.x
        dy = self.waypoint[1] - self.y
        distance_to_waypoint = (dx * dx + dy * dy) ** 0.5
        if distance_to_waypoint < self.reached_threshold:
            self.waypoint = self._random_waypoint()
            dx = self.waypoint[0] - self.x
            dy = self.waypoint[1] - self.y
            distance_to_waypoint = (dx * dx + dy * dy) ** 0.5
        desired_theta = math.degrees(math.atan2(dx, dy)) % 360
        heading_error = desired_theta - self.theta
        while heading_error > 180:
            heading_error -= 360
        while heading_error < -180:
            heading_error += 360
        self.omega = max(min(heading_error * 2.0, self.max_turn), -self.max_turn)
        self.v = min(distance_to_waypoint * 0.5, self.max_speed)
        theta_rad = math.radians(self.theta)
        self.x += self.v * dt * math.sin(theta_rad)
        self.y += self.v * dt * math.cos(theta_rad)
        self.theta = (self.theta + self.omega * dt) % 360
        self.x = max(min(self.x, 60), -60)
        self.y = max(min(self.y, 60), -60)
        self.battery = max(self.battery - 0.005 * (abs(self.v) + abs(self.omega)) * dt, 0)
        for i in range(self.motor_count):
            self.temps[i] += (0.01 * abs(self.v) - 0.005 * (self.temps[i] - 30)) * dt
            self.temps[i] = max(min(self.temps[i], 70), 25)
            self.rpm[i] = abs(self.v) * 100 + random.random() * 10
            self.volts[i] = 12.5 - 0.01 * abs(self.rpm[i]) + random.uniform(-0.05, 0.05)
            self.volts[i] = max(11, min(self.volts[i], 12.7))

    def payload(self) -> bytes:
        now = time.time()
        dt = now - self.last_update
        dt = max(min(dt, 0.1), 0.001)
        self.step(dt)
        self.last_update = now
        version = 1
        m = self.motor_count
        payload = struct.pack('<BBffff', version, m, self.battery, self.x, self.y, -self.theta)
        for arr in (self.temps, self.rpm, self.volts):
            payload += struct.pack('<' + 'f' * m, *arr)
        crc = crc16_ccitt(payload)
        payload += struct.pack('<H', crc)
        return payload


def mock_writer(pool: ClientPool, stop: threading.Event, motors: int, hz: int):
    sim = RobotSim(motors)
    period = 1.0 / max(hz, 1)
    next_t = time.perf_counter()
    while not stop.is_set():
        payload = sim.payload()
        frame = cobs_encode(payload)
        pool.broadcast(frame)
        next_t += period
        sleep_dur = next_t - time.perf_counter()
        if sleep_dur > 0:
            time.sleep(sleep_dur)
        else:
            next_t = time.perf_counter()


def main():
    ap = argparse.ArgumentParser(description='RS-485 to TCP bridge (raw COBS+CRC16), with optional mock generator')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=34453)
    ap.add_argument('--uart', default='/dev/serial0')
    ap.add_argument('--baud', type=int, default=512000)
    ap.add_argument('--mock', action='store_true', help='Generate mock frames instead of reading UART')
    ap.add_argument('--motors', type=int, default=4)
    ap.add_argument('--hz', type=int, default=100)
    args = ap.parse_args()

    # Receive-only: keep DE/RE low
    DigitalOutputDevice(17, active_high=True, initial_value=False)

    pool = ClientPool()
    stop = threading.Event()

    worker: Optional[threading.Thread] = None
    if args.mock:
        worker = threading.Thread(target=mock_writer, args=(pool, stop, args.motors, args.hz), daemon=True)
        worker.start()
        print(f"Mock mode ON: motors={args.motors}, hz={args.hz}")
    else:
        ser = serial.Serial(args.uart, args.baud, timeout=0.02)
        worker = threading.Thread(target=uart_reader, args=(ser, pool, stop), daemon=True)
        worker.start()
        print(f"UART mode ON: {args.uart} @{args.baud} baud")

    try:
        tcp_server(args.host, args.port, pool, stop)
    finally:
        stop.set()
        if worker:
            worker.join(timeout=1.0)


if __name__ == "__main__":
    main()
