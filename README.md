# DoralTelemetry — End‑to‑End Telemetry (Bot, Pi, Proxy, Website)

Modular telemetry stack for VEX V5 robots: a C++ PROS library on the robot, a Raspberry Pi RS‑485→TCP bridge, a PC‑side SSE proxy, and a React website with theme support.

[Kanban + Docs](https://www.notion.so/Doral-Telemetry-Features-Kanban-1fb83b8a79dd807db376e0dae9aa1ce0)

## Architecture
- Bot-End (VEX/PROS): Publishes COBS+CRC16 framed telemetry over UART/RS‑485, 0x00‑delimited.
- Pi-End (`wifiBridge.py`): Receives UART bytes and forwards raw frames over TCP (`0.0.0.0:34453`).
- PC-End:
  - `pc_proxy.py`: Connects to the Pi TCP stream, COBS+CRC16 validates, parses payload, serves JSON via SSE at `/stream`.
  - `website/`: React + Vite + Tailwind app that consumes SSE and renders live telemetry with selectable themes.

## Project Structure
- `Bot-End/Example-Project/`: PROS C++ library and example entry point.
  - Public API: `include/doraltelemetry/` (COBS + CRC16 telemetry).
  - Sources: `src/doraltelemetry/` and example `src/main.cpp`, `src/global.cpp`.
- `Pi-End/`: Raspberry Pi RS‑485 → TCP bridge (`wifiBridge.py`).
- `PC-End/`: Local SSE proxy (`pc_proxy.py`) + Website (`website/`).

## Bot Library (C++ / PROS)
- Namespace `doraltelemetry`; C++20.
- Public API (see `include/doraltelemetry/telemetry.hpp`):
  - `void init(pros::Serial* uart);`
  - `void submit(const float* temps, const float* rpm, const float* volt, int motorCount, float x, float y, float theta, float battery);`
  - Optional: `start_fake_task(motorCount=4)`, `stop_task()`.
- Payload layout (little‑endian), framed with COBS + `0x00`, CRC16‑CCITT appended:
  - `[u8 version=1][u8 motorCount][f32 battery][f32 x][f32 y][f32 theta][f32 temps[m]][f32 rpm[m]][f32 volt[m]][u16 crc16]`.

### Build (Library Archive)
- `cd Bot-End/Example-Project && make library`
- Outputs `bin/doraltelemetry.a` for PROS Depot usage.

## Raspberry Pi Bridge (RS‑485 → TCP)
- Wiring: TX GPIO14 → DI, RX GPIO15 → RO, DE/RE GPIO17 (held low = receive‑only).
- Enable UART on Pi (disable serial console, enable serial hardware).
- Install deps (Pi): `pip3 install pyserial gpiozero`
- Run (UART mode): `python3 Pi-End/wifiBridge.py` (listens on `0.0.0.0:34453`).
  - Forwards raw UART bytes (COBS+CRC16 frames, `0x00` delimited) to TCP clients.

### Pi Mock Mode (no robot required)
- Generate realistic COBS+CRC16 frames directly from the Pi:
  - `python3 Pi-End/wifiBridge.py --mock --motors 4 --hz 100`
- Flags:
  - `--motors`: number of motors in arrays (default 4)
  - `--hz`: publish rate for frames (default 100)
  - `--host`, `--port`: TCP listen address/port (defaults `0.0.0.0:34453`)
  - UART flags (ignored in mock): `--uart`, `--baud`

## PC Proxy (SSE)
- Deps (PC): `pip3 install Flask flask-cors`
- Run: `python3 PC-End/pc_proxy.py --pi-host 10.0.0.1 --pi-port 34453 --host 127.0.0.1 --port 9000`
  - Exposes SSE at `http://127.0.0.1:9000/stream`.
  - Quick check: `curl -N http://127.0.0.1:9000/stream` (should stream `data: { ... }`).

## Website (React + Vite + Tailwind)
- Requires Bun or Node; repo uses Bun lockfile.
- Install: `cd PC-End/website && bun install`
- Dev: `VITE_SSE_URL=http://127.0.0.1:9000/stream bun run dev`
- Open the printed local URL (typically `http://127.0.0.1:5173/`).

### Themes
- Options: Default, Blue Accents, Gruvbox Dark, Gruvbox Light.
- Persisted in `localStorage`; toggle via the settings button in the UI.

## End‑to‑End Test
1) Start the Pi bridge: `python3 Pi-End/wifiBridge.py`
2) Start the PC proxy: `python3 PC-End/pc_proxy.py --pi-host 10.0.0.1 --pi-port 34453`
3) In another terminal, start the website:
   - `cd PC-End/website && bun install`
   - `VITE_SSE_URL=http://127.0.0.1:9000/stream bun run dev`
4) Open the website and verify live updates (battery, motors, position).

Tip: Without hardware, use the mock SSE server instead of the proxy:
- `python3 PC-End/mock.py` then `VITE_SSE_URL=http://127.0.0.1:34453/stream bun run dev`.

Or, mock at the Pi layer and keep using the proxy and website as‑is:
- On Pi: `python3 Pi-End/wifiBridge.py --mock --motors 4 --hz 100`
- On PC: `python3 PC-End/pc_proxy.py --pi-host 10.0.0.1 --pi-port 34453`

## Coding Style
- C++: Namespace `doraltelemetry`, headers under `include/doraltelemetry/`, 4‑space indents.
- Python: 4‑space indents; focused modules and functions.

## Security & Defaults
- Receive‑only Pi (DE/RE low); no secrets in repo.
- Default UART: `/dev/serial0 @ 512000` baud. Default TCP: `10.0.0.1:34453`.
- If exposing the UI beyond localhost, add HTTPS and auth at the proxy layer.

## Conventional Commits
- Format: `type(scope): summary` (e.g., `feat(bot): add submit() payload layout`).
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
- Breaking changes: `feat!: ...` or footer `BREAKING CHANGE: ...`.

## License
MIT



