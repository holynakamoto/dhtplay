---
defract:
  id: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76
  type: bug
  status: active
  stage: review
  phase: 0
  total_phases: 1
  priority: normal
  source: manual
  branch_strategy: worktree
  mode: human-in-the-loop
  created_by: holynakamoto
  assignee: holynakamoto
---


## Story Brief

# Streaming to mobile VLC: fix URL output and add QR code

# Streaming to mobile VLC: fix URL output and add QR code

## What We're Building

When streaming to a phone via `--url`, dhtplay currently prints a hardcoded path that no longer matches what the installed version of webtorrent-cli actually serves — so the URL is a dead link. We will fix this by reading webtorrent's own startup output to get the real stream URL, substituting the Mac's LAN IP for "localhost" so the phone can reach it, and optionally rendering a QR code in the terminal so the URL can be opened on the phone with a camera tap instead of typing.

## Expected Outcome

- Running `dhtplay <infohash> --url` prints a URL that actually works when opened in mobile VLC — no more 404.
- The printed URL uses the Mac's LAN IP address, not "localhost", so a phone on the same Wi-Fi can reach it.
- If `qrencode` is installed, a scannable QR code appears in the terminal beneath the URL so the user never has to type it on the phone.
- If `qrencode` is not installed, the tool works exactly as before minus the QR code — no error, no change in exit behavior.

## Phase Outcomes

- **Phase 1: Fix URL output and add QR code** — The `--url` path reads the real stream path from webtorrent's startup output and substitutes the LAN IP so the phone can reach the stream, then renders an optional QR code for one-tap access on mobile. All existing test scenarios continue to pass.

## Out of Scope

- Changing how the non-`--url` (local VLC) path works — only the network-streaming branch is affected.
- Bundling or auto-installing `qrencode` — it is an optional shell dependency the user installs if they want QR codes.
- Supporting streaming to multiple devices simultaneously or managing multiple ports.

## Scope Summary

**Size:** 7 requirements, 7 acceptance criteria, 1 implementation phase
**Key decisions:**
- Read webtorrent's stdout with a background daemon thread and a 30-second timeout, falling back to the root URL if no URL line is found within the window.
- Use `subprocess.run(["qrencode", ...])` guarded by `OSError`/`FileNotFoundError` for graceful degradation when `qrencode` is absent.
**Biggest risk:** webtorrent's stdout format varies by version — the URL-matching regex must be broad enough to match common patterns without matching noise, and the 30-second fallback ensures the tool never hangs.

## Context

The `--url` branch in `main()` (lines 183–197 of `dhtplay`) currently hardcodes `/0` as the file path (`http://{lan_ip}:{port}/0`). This path matched an older version of webtorrent-cli but no longer matches what the current installed version serves. A `_find_stream_url` helper was referenced in the project profile but was removed before ever being wired up. The fix reinstates that scanning approach: launch webtorrent with `stdout=subprocess.PIPE`, read lines in a background daemon thread, match the first URL containing the port number, swap `localhost`/`127.0.0.1` for the LAN IP, and print it. If no URL is found within 30 seconds, fall back to `http://{lan_ip}:{port}/` so the tool never produces a silent wrong answer. The QR code addition is a thin wrapper: after printing the URL, attempt `qrencode -t ansiutf8 <url>`; catch `OSError`/`FileNotFoundError` to skip silently. Test scenario S13 currently asserts `/0` appears in output — that assertion must be updated to mock webtorrent stdout and assert the real URL path.

## Requirements

### URL fix

- R1: When `--url` is passed, `dhtplay` launches webtorrent with `stdout=subprocess.PIPE` and reads its output in a background daemon thread to find the first line containing a URL matching `http://localhost:{port}/...` or `http://127.0.0.1:{port}/...`.
- R2: Any occurrence of `localhost` or `127.0.0.1` in the extracted URL is replaced with the LAN IP returned by `get_lan_ip()` before printing.
- R3: If no matching URL is found within 30 seconds, fall back to printing `http://{lan_ip}:{port}/` and continue waiting for the process — no error, no non-zero exit.
- R4: The `--port` value propagates correctly to both the webtorrent command and the URL (hardcoded and fallback).

### QR code

- R5: After printing the URL, if `qrencode` is available on `PATH`, run `qrencode -t ansiutf8 <url>` and allow its output to write to the terminal.
- R6: If `qrencode` is not installed (raises `OSError` or `FileNotFoundError`), skip silently — no error message, no change in exit code.

### Tests

- R7: Existing test scenarios S01–S16 must continue to pass unchanged. S13 must be updated to mock `proc.stdout` with a webtorrent URL announcement line and assert the printed URL contains the LAN IP (not `localhost`) and the path from the mocked output. New scenarios S17 (qrencode present) and S18 (qrencode absent) must be added.

## Acceptance Criteria

- [ ] `python3 test_dhtplay.py` exits 0 with all scenarios passing.
- [ ] S13 asserts that the printed URL contains the path from the mocked webtorrent stdout and that `localhost` has been replaced with the mocked LAN IP (not the hardcoded `/0`).
- [ ] S17 asserts that when `qrencode` is mocked as available, `subprocess.run` is called once with `["qrencode", "-t", "ansiutf8", <url>]`.
- [ ] S18 asserts that when `qrencode` raises `FileNotFoundError`, the exit code is 0 and stderr is empty.
- [ ] Manual check: `./dhtplay <hex-hash> --url` prints a URL containing the host machine's LAN IP and a path matching what webtorrent announces; a QR code appears in the terminal if `qrencode` is installed.
- [ ] S14 (KeyboardInterrupt calls `proc.terminate()`) continues to pass — the terminate path is unchanged.
- [ ] S11 and S15 (non-`--url` path and `--port` propagation) continue to pass with no regressions.

## Implementation Phases

### Phase 1: Fix URL output and add QR code
**Scope:** Rewrite the `--url` branch to pipe and scan webtorrent's stdout for the real stream URL, substitute the LAN IP, print the URL, and optionally render a QR code. Update S13 and add S17/S18.
**Files:**
- `dhtplay` — add `_find_stream_url(proc, port, timeout=30)` helper (background thread + `queue.Queue`); add `_render_qr(url)` helper; rewrite the `--url` branch in `main()` to call both, handle the fallback case, and preserve the existing `KeyboardInterrupt` → `proc.terminate()` path.
- `test_dhtplay.py` — update S13 to mock `proc.stdout` as an iterator yielding a URL announcement line; add S17 and S18.
**Verification:**
- `python3 test_dhtplay.py` exits 0 with all tests passing.
- `python3 -m unittest test_dhtplay.S13_UrlFlag test_dhtplay.S17_QrCode test_dhtplay.S18_QrCodeAbsent` passes.
- `./dhtplay --help` still shows `--url` and `--port` in usage (smoke check, no process spawn needed).
**Estimated effort:** Small

## Edge Cases

- **webtorrent never prints a URL (newer version changes output format):** fall back to `http://{lan_ip}:{port}/` after 30-second timeout; the user gets a root URL that may or may not work, but the tool does not hang or crash.
- **webtorrent prints the URL on stderr instead of stdout:** the scan only reads stdout; the fallback URL is printed silently — no error.
- **LAN IP detection fails (no Wi-Fi):** `get_lan_ip()` already returns `127.0.0.1`; the URL will use localhost but the tool will not crash.
- **`qrencode` is installed but exits non-zero:** dhtplay does not check `qrencode`'s return code — it renders what it can and moves on.
- **webtorrent exits before printing a URL:** the background thread's iterator terminates naturally; `_find_stream_url` returns `None`; the fallback URL is printed.

## Technical Notes

`_find_stream_url` should use a daemon thread (so it does not block process exit) and a `queue.Queue`. The thread reads `proc.stdout` line by line, puts the first match into the queue, then continues draining (to prevent pipe buffer deadlock). The main thread calls `q.get(timeout=30)`, catching `queue.Empty` to trigger the fallback.

URL matching regex: `re.search(r'https?://\S*' + re.escape(str(port)) + r'\S*', line)`. The port number is the stable anchor across webtorrent-cli versions; matching anything before and after it captures any path format.

After the URL is found and printed (or the fallback fires), the existing `proc.wait()` / `KeyboardInterrupt` → `proc.terminate()` pattern is preserved verbatim.

`qrencode -t ansiutf8` outputs UTF-8 block characters and ANSI escape codes suitable for modern terminals. The `-t ansiutf8` format produces a compact pixel-dense rendering.

S13 currently asserts `self.assertIn("/0", output)` — this assertion must be replaced. The new mock must set `proc_mock.stdout` to an iterator (e.g. `iter(["Server running at: http://localhost:8888/Movie.mkv\n"])`) and the test should assert the printed URL contains `192.168.1.100` and `/Movie.mkv`.

### Dependencies

No new Python dependencies. `qrencode` is an optional system tool (`brew install qrencode` on macOS); its absence must never cause a failure.

## Implementation Notes

## Phase 1: Fix URL output and add QR code

### What was built

**`dhtplay` changes:**
- Added `import queue` and `import threading`
- Added `_find_stream_url(proc, port, timeout=30)`: starts a daemon thread that reads `proc.stdout` line by line and puts the first URL matching `r'https?://\S*{port}\S*'` into a `queue.Queue`. Main thread calls `q.get(timeout=30)`, returning `None` on `queue.Empty`.
- Added `_render_qr(url)`: calls `subprocess.run(["qrencode", "-t", "ansiutf8", url])`, catching `(OSError, FileNotFoundError)` silently.
- Rewrote `--url` branch: launches webtorrent with `stdout=subprocess.PIPE, text=True`, calls `_find_stream_url`, substitutes `localhost`/`127.0.0.1` with LAN IP via `re.sub`, falls back to `http://{lan_ip}:{port}/` on timeout, prints URL, calls `_render_qr`, then preserves existing `proc.wait()` / `KeyboardInterrupt → proc.terminate()` path.

**`test_dhtplay.py` changes:**
- S13 rewritten: `test_url_flag_prints_http_url` mocks `proc_mock.stdout = iter(["Server running at: http://localhost:8888/Movie.mkv\n"])` and asserts output contains `192.168.1.100` and `/Movie.mkv` (not `localhost`). `test_url_flag_no_vlc` patches `_find_stream_url` directly to return `None` quickly.
- S14 updated: added `patch("dhtplay._find_stream_url", return_value=None)` and `patch("dhtplay._render_qr")` to prevent the 30-second queue timeout (MagicMock's default `__iter__` yields nothing, so the reader exits immediately and the main thread would block).
- S17 added: asserts `subprocess.run` is called with `["qrencode", "-t", "ansiutf8", "http://192.168.1.100:8888/Movie.mkv"]` when `_find_stream_url` returns `"http://localhost:8888/Movie.mkv"`.
- S18 added: asserts exit code 0 and empty stderr when `subprocess.run` raises `FileNotFoundError`.

### Test results
41/41 passing. Runtime: 0.06s.
