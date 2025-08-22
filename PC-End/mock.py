import struct
import time
import random
import json
import math
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

# --- Robot state for realistic movement ---
class RobotSim:
    def __init__(self):
        self.x = random.uniform(-36, 36)
        self.y = random.uniform(-36, 36)
        self.theta = random.uniform(0, 360)  # CW positive, 0 = y-up
        self.v = 0.0         # Forward velocity (inches/sec)
        self.omega = 0.0     # Rotational velocity (deg/sec)
        self.last_update = time.time()
        self.battery = random.uniform(80, 100)
        self.motor_count = 4
        self.temps = [random.uniform(30, 55) for _ in range(self.motor_count)]
        self.rpm = [random.uniform(0, 600) for _ in range(self.motor_count)]
        self.volts = [random.uniform(11, 13) for _ in range(self.motor_count)]
        # Waypoint navigation
        self.waypoint = self._random_waypoint()
        self.reached_threshold = 2.0  # inches
        self.max_speed = 3.0  # inches/sec
        self.max_turn = 90.0  # deg/sec

    def _random_waypoint(self):
        # Field is 144x144, clamp to [-60, 60] for margin
        return (random.uniform(-60, 60), random.uniform(-60, 60))

    def step(self, dt):
        # Make simulation 10x faster
        dt = dt * 10

        # Check if we've reached the current waypoint
        dx = self.waypoint[0] - self.x
        dy = self.waypoint[1] - self.y
        distance_to_waypoint = (dx**2 + dy**2)**0.5

        if distance_to_waypoint < self.reached_threshold:
            # Pick a new waypoint
            self.waypoint = self._random_waypoint()
            dx = self.waypoint[0] - self.x
            dy = self.waypoint[1] - self.y
            distance_to_waypoint = (dx**2 + dy**2)**0.5

        # Calculate desired heading to waypoint (CW positive, 0 = y-up)
        desired_theta = math.degrees(math.atan2(dx, dy))
        desired_theta = desired_theta % 360

        # Calculate heading error
        heading_error = desired_theta - self.theta
        # Normalize to [-180, 180]
        while heading_error > 180:
            heading_error -= 360
        while heading_error < -180:
            heading_error += 360

        # Set rotational velocity to steer toward waypoint
        self.omega = max(min(heading_error * 2.0, self.max_turn), -self.max_turn)

        # Set forward velocity based on distance to waypoint
        self.v = min(distance_to_waypoint * 0.5, self.max_speed)

        # Integrate velocity to position and heading (CW positive, 0 = y-up)
        theta_rad = math.radians(self.theta)
        self.x += self.v * dt * math.sin(theta_rad)
        self.y += self.v * dt * math.cos(theta_rad)
        self.theta += self.omega * dt

        # Clamp position to |x|,|y| < 60
        self.x = max(min(self.x, 60), -60)
        self.y = max(min(self.y, 60), -60)

        # Wrap theta to [0, 360)
        self.theta = self.theta % 360

        # Simulate battery drain
        self.battery -= 0.005 * (abs(self.v) + abs(self.omega)) * dt
        self.battery = max(self.battery, 0)

        # Simulate motor temps, rpm, volts
        for i in range(self.motor_count):
            # Temp rises with velocity, cools otherwise
            self.temps[i] += (0.01 * abs(self.v) - 0.005 * (self.temps[i] - 30)) * dt
            self.temps[i] = max(min(self.temps[i], 70), 25)
            # RPM proportional to velocity + noise
            self.rpm[i] = abs(self.v) * 100 + random.random() * 10
            # Voltage drops slightly with load
            self.volts[i] = 12.5 - 0.01 * abs(self.rpm[i]) + random.uniform(-0.05, 0.05)
            self.volts[i] = max(11, min(self.volts[i], 13))

    def get_state(self):
        return {
            "version": 1,
            "motorCount": self.motor_count,
            "battery": self.battery,
            "x": self.x,
            "y": self.y,
            "theta": -self.theta,
            "motorTemperature": self.temps[:],
            "motorRpm": self.rpm[:],
            "motorVoltage": self.volts[:],
            "ts": time.time()
        }

robot_sim = RobotSim()

def make_payload(motor_count=4):
    # Use robot_sim for realistic movement
    now = time.time()
    dt = now - robot_sim.last_update
    dt = max(min(dt, 0.1), 0.001)
    robot_sim.step(dt)
    robot_sim.last_update = now
    state = robot_sim.get_state()
    version = state["version"]
    battery = state["battery"]
    x = state["x"]
    y = state["y"]
    theta = state["theta"]
    temps = state["motorTemperature"]
    rpm = state["motorRpm"]
    volts = state["motorVoltage"]
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

def telemetry_generator(motor_count, hz):
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
    ap.add_argument('--hz', type=int, default=100)
    args = ap.parse_args()
    print(f"Mock RPi SSE server listening on http://{args.host}:{args.port}/stream (motors={args.motors}, {args.hz}Hz)")
    app.run(host=args.host, port=args.port, threaded=True)
