# VEX Telemetry Suite

Modular telemetry for VEX V5 robots using PROS (bot), a Raspberry Pi RS‑485 bridge, and a Wi‑Fi client UI. The design is receive‑only: the robot streams JSON lines over UART; the Pi relays them via HTTP Server‑Sent Events (SSE) and serves a Gruvbox‑dark web client.

[KanBan + Docs](https://www.notion.so/Doral-Telemetry-Features-Kanban-1fb83b8a79dd807db376e0dae9aa1ce0)

## Core Features
- Real-time telemetry from the VEX brain via RS‑485 → Raspberry Pi.
- Bot → Pi uses COBS + CRC16 binary frames (200 Hz target).
- PC Python app starts a local Gruvbox UI and proxies data as JSON.
- Simple bot API: user calls a function with motor arrays + pose + battery.

## Repo Layout
- `Bot-End/Example-Project/`: PROS project (C++), UART JSON telemetry.
- `Pi-End/`: Python RS‑485 → SSE bridge + web client.

## Bot Library (PROS Depot)
- Library name: `doraltelemetry` (this project builds a library archive).
- Public header: `include/doraltelemetry/telemetry.hpp`.
- API:
  - `void doraltelemetry::init(pros::Serial* uart);`
  - `void doraltelemetry::submit(const float* temps, const float* rpm, const float* volt, int motorCount, float x, float y, float theta, float battery);`
  - Optional: `start_fake_task(motorCount=4)`, `stop_task()`.
- Supported motors: pass `motorCount` (e.g., 4 or 6). Unused arrays can be null; extra values ignored.
- Packet format: `[ver=1][motorCount][battery,x,y,theta][temps[m]][rpm[m]][volt[m]][crc16]` COBS-framed with `0x00` delimiter.

## Pi Setup (RS‑485 → TCP)
1. Wire RS‑485 transceiver (MAX485) to Pi:
   - TX: GPIO 14 → DI, RX: GPIO 15 → RO
   - DE/RE: GPIO 17 (low = receive)
2. Enable UART on the Pi (disable serial console; keep serial hardware enabled).
3. Run `python3 Pi-End/wifiBridge.py` to start TCP server at `0.0.0.0:34453`.
   - The server forwards raw COBS-framed bytes from `/dev/serial0`.

## PC UI (Local Gruvbox)
- Start: `python3 PC-End/telemetry_ui.py` (defaults: UI at `http://127.0.0.1:9000`, Pi at `10.0.0.1:34453`).
- The Python app connects to the Pi TCP stream, validates COBS+CRC, converts to JSON, and serves SSE at `/stream` + a minimal Gruvbox UI at `/`.
- Flags: `--pi-host`, `--pi-port`, `--host`, `--port`.
- Simulate (no Pi needed): add `--simulate` (optional: `--sim-motors 6 --sim-hz 200`).

## Notes
- Receive-only design; RS‑485 direction pin held low (listen).
- Library is bot-only; PC UI is separate from PROS depot packaging.

## License
MIT



