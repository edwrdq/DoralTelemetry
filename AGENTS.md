# Repository Guidelines

## Project Structure & Module Organization
- `Bot-End/Example-Project/`: PROS C++ library and example entry point.
  - Public API: `include/doraltelemetry/` (COBS + CRC16 telemetry).
  - Sources: `src/doraltelemetry/` and example `src/main.cpp`, `src/global.cpp`.
- `Pi-End/`: Raspberry Pi RS‑485 → TCP bridge (`wifiBridge.py`).
- `PC-End/`: Local UI + SSE proxy (`telemetry_ui.py`).
- `README.md`: Setup and usage.

## Build, Test, and Development Commands
- Build bot library (archive):
  - `cd Bot-End/Example-Project && make library`
  - Outputs `bin/doraltelemetry.a` for PROS Depot usage.
- Build full bot image (optional):
  - `cd Bot-End/Example-Project && make`
- Run Pi bridge (COBS frames over TCP):
  - `python3 Pi-End/wifiBridge.py` (listens on `0.0.0.0:34453`).
- Run local UI/proxy:
  - `python3 PC-End/telemetry_ui.py` then open `http://127.0.0.1:9000/`.
  - Flags: `--pi-host 10.0.0.1 --pi-port 34453`.

## Coding Style & Naming Conventions
- C++ (C++20):
  - Namespace `doraltelemetry`; headers under `include/doraltelemetry/`.
  - Use clear identifiers; avoid one‑letter names. 4‑space indents.
  - Keep headers minimal; prefer `.hpp` for interfaces, `.cpp` for impl.
- Python: 4‑space indents; small, focused modules and functions.
- No enforced formatter in repo; match existing style and avoid trailing whitespace.

## Testing Guidelines
- No unit test framework configured. Validate end‑to‑end:
  - Send frames from bot via `doraltelemetry::submit(...)` at 200 Hz.
  - Confirm Pi bridge forwards bytes; UI shows live values and charts.
- Prefer small, deterministic helpers for future unit tests (e.g., COBS/CRC enc/dec).

## Commit & Pull Request Guidelines
- Conventional Commits are required for both commit messages and PR titles.
  - Format: `type(scope): summary` (e.g., `feat(bot): add submit() payload layout`).
  - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
  - Breaking changes: `feat!: ...` or footer `BREAKING CHANGE: ...`.
- Commits: keep small and focused; include rationale in body when non-obvious.
- PRs: title follows Conventional Commits; body includes motivation, changes, testing notes.
  - Link related issues; attach UI screenshots and sample payloads when relevant.

## Security & Configuration Tips
- Pi runs receive‑only (DE/RE low); no secrets in repo.
- Default UART: `/dev/serial0` @ `512000` baud. Default TCP: `10.0.0.1:34453`.
- If exposing UI beyond localhost, add HTTPS and auth at the proxy layer.
