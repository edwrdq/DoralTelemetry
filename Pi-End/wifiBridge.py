import serial
import time
from gpiozero import DigitalOutputDevice
from flask import Flask, Response, render_template_string

"""
RS485 -> WiFi Bridge
--------------------
GPIO 14(TX) -> MAX485 DI
GPIO 15(RX) -> MAX485 RO
GPIO 17 -> MAX485 DE/RE (low for receive, high for transmit)
"""

#----- RS-485 (UART) Configuration -----

UART_DEV = '/dev/serial0'  # UART device
BAUD = 512_000
ser485 = serial.Serial(UART_DEV, BAUD, timeout=0.02)

dir_pin = DigitalOutputDevice(17, active_high=True, initial_value=False)

#----- Flask App -----

app = Flask(__name__)

def brain_reader():
    """Reads data from the serial port and yields it for SSE."""
    buf = bytearray()
    while True:
        buf.extend(ser485.read(1024))
        while b"\n" in buf:
            pkt, _, buf = buf.partition(b"\n")
            yield f"data: {pkt.decode('utf-8')}\n\n"
        time.sleep(0.001) # Small delay to prevent busy-waiting

@app.route('/')
def stream():
    """SSE endpoint to stream data from the brain."""
    return Response(brain_reader(), mimetype='text/event-stream')

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=9000, threaded=True)
    except KeyboardInterrupt:
        print("bye")
