# DoralTelemetry — PC-End (UI + SSE Proxy)

This folder contains the local telemetry UI (React + Vite + Tailwind + Mosaic layout) and a PC-side SSE proxy that connects to the Raspberry Pi RS‑485→TCP bridge and rebroadcasts telemetry as Server-Sent Events (SSE) for the UI.

## Architecture
- Bot-End (VEX/PROS): Publishes COBS+CRC16 framed telemetry over UART/RS‑485.
- Pi-End (`wifiBridge.py`): Receives bytes from UART and exposes them over TCP on a fixed port (default `34453`).
- PC-End:
  - `pc_proxy.py`: Connects to the Pi’s TCP port, decodes COBS frames, CRC checks, parses payload, and serves JSON as SSE at `/stream`.
  - `website/`: React app that listens to the SSE URL and renders live telemetry (motors, battery, field view). Includes theme switching.

## Requirements
- Python 3.11 (see `.python-version`)
- Bun (v1+) for web dev (`bun install` / `bun run dev`)

## Quick Start (Real Hardware)
1) On the Pi (bridge):
- `python3 Pi-End/wifiBridge.py`
  - Listens on `0.0.0.0:34453` and forwards raw frames over TCP.

2) On your PC (proxy):
- `python3 pc_proxy.py --pi-host 10.0.0.1 --pi-port 34453 --port 9000`
  - Connects to the Pi and exposes SSE at `http://127.0.0.1:9000/stream`.

3) On your PC (website):
- `cd website`
- `bun install`
- `VITE_SSE_URL=http://127.0.0.1:9000/stream bun run dev`
- Open the printed local URL (typically `http://127.0.0.1:5173/`).

## Quick Start (Mock Data)
Use this when you don’t have the Pi/robot running.

- `python3 mock.py` (serves SSE at `http://127.0.0.1:34453/stream`)
- In another terminal:
  - `cd website`
  - `bun install`
  - `VITE_SSE_URL=http://127.0.0.1:34453/stream bun run dev`

## PC Proxy (`pc_proxy.py`)
Connects to the Pi TCP bridge, reads COBS-framed packets delimited by `0x00`, CRC16-CCITT checks them, parses payload, and broadcasts JSON lines via SSE at `/stream`.

Flags:
- `--pi-host`: Pi host or IP (default `10.0.0.1`)
- `--pi-port`: Pi TCP port (default `34453`)
- `--host`: HTTP listen host (default `127.0.0.1`)
- `--port`: HTTP listen port (default `9000`)

Test SSE quickly:
- `curl -N http://127.0.0.1:9000/stream`

## Website (`website/`)
- React + Vite + Tailwind + `react-mosaic-component`.
- Reads SSE URL from `VITE_SSE_URL`. If not provided, defaults to `http://127.0.0.1:9000/stream`.
- The top bar shows a battery icon and a gear (settings) to the right. Click the gear to open the theme menu.

Themes:
- Default, Blue Accents, Gruvbox Dark, Gruvbox Light
- Persist in `localStorage`.

Run with Bun:
- `cd website`
- `bun install`
- `VITE_SSE_URL=http://127.0.0.1:9000/stream bun run dev`

Build:
- `bun run build` (or `vite build`)

## Telemetry Message (JSON fields)
The proxy and mock both produce JSON payloads with:
- `version`: number
- `motorCount`: number
- `battery`: percentage (0–100)
- `x`, `y`: inches (field is 144x144, origin center, y-up)
- `theta`: degrees
- `motorTemperature[]`: °C
- `motorRpm[]`: RPM
- `motorVoltage[]`: V (mock clamps to ≤ 12.7V)
- `ts`: unix time

## Troubleshooting
- No data in UI:
  - Verify the proxy prints its listening URL and that the website `VITE_SSE_URL` matches.
  - `curl -N <VITE_SSE_URL>` should stream JSON lines (each prefixed with `data:`).
  - Check firewall rules for the Pi TCP port and your local proxy port.
- Pi bridge reachable?
  - From PC: `nc -vz 10.0.0.1 34453` to confirm TCP connectivity.
- CORS:
  - Proxy enables CORS; you shouldn’t need extra configuration for local dev.

## Repo Conventions
- Conventional Commits for PRs and commits: `type(scope): summary`.
- Keep changes focused and include rationale in commit bodies when non-obvious.
