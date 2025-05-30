import asyncio, json, serial, time, socket
from gpiozero import DigitalOutputDevice

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

#----- TCP Settings -----

HOST = '0.0.0.0'
PORT = 9000
clients = set()

#----- server ------

async def brain_reader():
    buf = bytearray()
    while True:
        buf.extend(ser485.read(1024)) #2ms read
        while b"\n" in buf:
            pkt,_, buf = buf.partition(b"\n")
            dead = []
            for c in clients:
                try:
                    c.sendall(pkt + b"\n") # send packet to all clients with flag
                except OSError:
                    dead.append(c)
            for c in dead:
                clients.discard(c) 
        await asyncio.sleep(0)

async def tcp_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv=setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    srv.setblocking(False)
    print(f"[INFO] listening on {HOST}:{PORT}")
    loop = asyncio.get_running_loop()
    while True:
        client, addr = await loop.run_in_executor(None, srv.accept)
        client.setblocking(False)
        clients.add(client)
        print(f"[INFO] client connected: {addr}")

async def main():
    await asyncio.gather(brain_reader(), tcp_server())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("bye")
