import socket
import serial
import threading
from gpiozero import DigitalOutputDevice

"""
RS485 -> TCP Bridge
-------------------
GPIO 14(TX) -> MAX485 DI
GPIO 15(RX) -> MAX485 RO
GPIO 17 -> MAX485 DE/RE (low for receive, high for transmit)

Serves raw COBS-framed bytes over TCP :34453 to any clients.
Frames are delimited by 0x00. No parsing/validation here.
"""

#----- RS-485 (UART) Configuration -----
UART_DEV = '/dev/serial0'  # UART device
BAUD = 512_000
ser485 = serial.Serial(UART_DEV, BAUD, timeout=0.02)

dir_pin = DigitalOutputDevice(17, active_high=True, initial_value=False)


def client_pump(conn: socket.socket):
    try:
        while True:
            data = ser485.read(1024)
            if not data:
                continue
            conn.sendall(data)
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def tcp_server(host='0.0.0.0', port=34453):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(5)
    print(f"RS485 TCP bridge listening on {host}:{port}")
    try:
        while True:
            conn, addr = s.accept()
            print(f"client connected: {addr}")
            t = threading.Thread(target=client_pump, args=(conn,), daemon=True)
            t.start()
    finally:
        s.close()


if __name__ == "__main__":
    try:
        tcp_server()
    except KeyboardInterrupt:
        print("bye")

