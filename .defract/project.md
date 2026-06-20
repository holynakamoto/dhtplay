---
defract:
  version: 1
  generated_at: "2026-06-20T22:17:00Z"
  updated_at: "2026-06-20T22:17:00Z"
  source: extracted
---

# Project Profile

## Overview

`dhtplay` is a single-file Python CLI tool that takes a BitTorrent infohash (hex, base32, or full magnet URI), builds a magnet link, and streams the torrent in VLC via `webtorrent-cli`.

## Stack

- **Runtime**: Python 3 (CPython; shebang `#!/usr/bin/env python3`)
- **External dependency**: `webtorrent-cli` (Node.js, installed globally via npm)
- **External dependency**: VLC (launched by webtorrent via `--vlc`)
- **Testing**: Python `unittest` (stdlib), with `unittest.mock`
- **Package manager**: none (single executable script, no pyproject.toml)
- **CI/CD**: none

## Conventions

- Single executable file named `dhtplay` (no `.py` extension) with a `#!/usr/bin/env python3` shebang — loaded by tests via `importlib.machinery.SourceFileLoader`
- `argparse` for CLI argument parsing
- Functions return values or `None`; errors surface as `ValueError` (internal) or `sys.exit` codes (CLI boundary)
- Exit codes: `0` success, `2` webtorrent not found, `3` launch failure
- `subprocess.Popen` (non-blocking) used for launching webtorrent/VLC; `subprocess.run` for side-car queries (`which`, `ipconfig`)
- Tests in `test_dhtplay.py` use `patch` to mock `subprocess.Popen` and `find_webtorrent`; scenarios named `S01`–`S12` with explicit PASS/FAIL criteria

## File Structure

```
dhtplay/
├── dhtplay           # main executable (Python 3, ~240 lines)
├── test_dhtplay.py   # unittest suite, 12 scenario classes, ~395 lines
└── __pycache__/      # compiled bytecode (auto-generated)
```

## Key Dependencies

### External (runtime, not pip-managed)
- `webtorrent-cli` — BitTorrent DHT client with HTTP streaming and VLC integration; resolved via hardcoded candidates (`/opt/homebrew/bin/webtorrent`, `/usr/local/bin/webtorrent`) or `which`
- VLC — media player; invoked by webtorrent via `--vlc`

### Standard library
- `argparse`, `base64`, `re`, `socket`, `subprocess`, `threading`, `urllib.parse`

## Build Commands

| Command | Description |
|---------|-------------|
| `python3 test_dhtplay.py` | Run the full test suite with PASS/FAIL summary |
| `./dhtplay <infohash>` | Stream an infohash in VLC |
| `./dhtplay <infohash> --dry-run` | Print the magnet URI without launching VLC |
| `./dhtplay <infohash> --url` | Print a LAN-accessible HTTP stream URL and launch |

## Project-Specific Notes

- The `_find_stream_url` function (lines 111–137) exists to scan webtorrent's stdout for the actual file path URL (e.g. `/Movie.mkv`) but is **not called** in the `--url` path of `main()` — the `--url` branch launches webtorrent without capturing stdout and prints only the root URL.
- macOS-specific LAN IP detection: `get_lan_ip()` queries `en0`/`en1`/`en2` via `ipconfig getifaddr` to avoid VPN tunnels winning the routing decision.
- The tracker list (`TRACKERS`) is hardcoded; `--no-trackers` omits them entirely.
