# Telemetry Website (React + Vite + Tailwind)

The website renders live robot telemetry via Server-Sent Events (SSE). It’s designed to be run alongside the PC-side proxy (`pc_proxy.py`) that connects to the Raspberry Pi TCP bridge.

## Run (with Bun)
- `bun install`
- `VITE_SSE_URL=http://127.0.0.1:9000/stream bun run dev`
- Open the printed local URL (typically `http://127.0.0.1:5173/`).

Notes:
- `VITE_SSE_URL` points at an SSE endpoint (the PC proxy). If not set, the app defaults to `http://127.0.0.1:9000/stream`.
- For mock data, run `python3 ../mock.py` and set `VITE_SSE_URL=http://127.0.0.1:34453/stream`.

## Features
- Mosaic layout: motor cards and field view panes can be arranged, resized, and toggled.
- Live telemetry fields: battery, motor temps/rpm/volts, pose on field.
- Settings (gear icon next to battery): theme picker
  - Default, Blue Accents, Gruvbox Dark, Gruvbox Light (persists in localStorage)

## Build
- `bun run build`
