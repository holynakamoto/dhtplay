---
defract:
  id: task-reviewing-url-hardening-diff-head-port-01kvve65x7kb
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

# Simplify --url output: drop redirect server, QR-encode direct file URL, add LAN reachability probe

# Simplify --url output: drop redirect server, QR-encode direct file URL, add LAN reachability probe

## What We're Building

The `--url` flag currently hands the user a short redirect URL that bounces through a locally-running redirect server. The review session concluded that this redirect hop is unnecessary (QR codes make URL length irrelevant) and is itself a suspect for remote VLC playback failures. This task removes the redirect server entirely, gives VLC and the QR code the direct long file URL from webtorrent's streaming server, and adds a LAN reachability probe so the tool fails fast with a clear error instead of printing a URL that cannot be reached.

## Expected Outcome

- Running `dhtplay <hash> --url` outputs and QR-encodes the direct LAN-accessible file URL, with no redirect hop in the path
- If webtorrent's streaming server cannot be reached from the machine's LAN IP (bound to localhost only), the tool exits with an error before printing anything to the user
- The `--short-port` CLI argument is removed; the tool no longer starts a secondary redirect server
- Tests are updated to reflect the direct URL format, the removed redirect-server tests are dropped, and a new test covers the reachability-probe failure path

## Phase Outcomes

- **Phase 1: Remove redirect server, add reachability probe, update tests** — Builders using `--url` receive a direct playable URL instead of a short redirect hop, and the tool fails fast with a clear error if the streaming server is not reachable from the LAN — rather than printing a URL that silently fails when opened on another device.

## Out of Scope

- The zero-payload-bytes problem (webtorrent stalling mid-download for some magnets) — this is a swarm health issue, not a code defect, tracked separately
- The WebTorrent/aria2 hybrid fallback — a separate follow-up task
- Changes to how webtorrent-cli is discovered, launched, or how trackers are configured

## Scope Summary

**Size:** 14 requirements, 5 acceptance criteria, 1 implementation phase
**Key decisions:**
- Reachability probe fires after URL resolution (server is guaranteed up), before printing anything
- Exit code 3 reused for probe failure (fits existing "launch failure" category; avoids adding a new exit code)
- `stdout` is not set on the `--url` Popen call, letting webtorrent's TUI pass through
**Biggest risk:** Existing S13–S18 tests are partially broken with the current code; the fix must add correct mocks (proc.poll, urlopen, socket probe) or those scenarios will still fail.

## Context

The `--url` branch in `main()` (lines 229–294 of `dhtplay`) currently launches webtorrent with `stdout=subprocess.DEVNULL`, polls `http://localhost:{port}/webtorrent/{ih_hex}/` for a directory listing, resolves a file URL, then starts a secondary HTTP redirect server on `short_port` (default: `port + 1`). The QR code and terminal output use the short redirect URL, not the file URL. The redirect server is extraneous now that QR codes handle long URLs, and suppressing stdout causes webtorrent to exit prematurely on some versions. The reachability probe addresses the silent failure case: webtorrent may bind only to 127.0.0.1 (making the printed URL unreachable from the LAN), but the local polling loop still succeeds since it hits localhost.

## Requirements

### Redirect Server Removal

- R1: The `--short-port` CLI argument is removed from argparse (currently lines 196–199 of `dhtplay`).
- R2: The secondary HTTP redirect server (`http.server.BaseHTTPRequestHandler`, `HTTPServer`, and the daemon thread that runs it) is removed from the `--url` branch of `main()`.
- R3: The `KeyboardInterrupt` handler in the `--url` branch calls only `proc.terminate()` — no `redir.shutdown()`.
- R4: The lazy import `from http.server import BaseHTTPRequestHandler, HTTPServer` inside the `--url` branch is removed.

### Direct URL Output

- R5: When `--url` is given, `dhtplay` prints and QR-encodes the direct LAN file URL (e.g., `http://{lan_ip}:{port}/webtorrent/{ih_hex}/Movie.mkv`) instead of a short redirect URL.
- R6: The printed URL must use the LAN IP returned by `get_lan_ip()`, not `localhost` or `127.0.0.1`.
- R7: If no specific file URL is resolved within the 120-second timeout (directory listing yields no video-extension href), the fallback directory URL `http://{lan_ip}:{port}/webtorrent/{ih_hex}/` is printed and QR-encoded.

### LAN Reachability Probe

- R8: After the file URL is resolved (or the fallback directory URL is set), `dhtplay` performs a TCP socket probe to `(lan_ip, port)` with a 2-second timeout using `socket.create_connection`.
- R9: If the probe raises `OSError`, `dhtplay` prints a descriptive error to stderr — e.g., `dhtplay: streaming server not reachable at {lan_ip}:{port} — is webtorrent bound to 0.0.0.0?` — and exits with code 3.
- R10: The probe runs after URL resolution but before printing anything about the URL to stdout.
- R11: The socket opened by the probe is closed in a `finally` block regardless of outcome.

### subprocess.Popen call

- R12: The `subprocess.Popen` call in the `--url` branch does not set `stdout` to `subprocess.DEVNULL` — webtorrent's stdout passes through to the terminal so its TUI and progress output remain visible.

### Test Updates

- R13: S13 (`S13_UrlFlag`) tests are updated to mock `proc.poll.return_value = None` (keeps the while loop alive), mock `urllib.request.urlopen` returning an HTML page with a `.mkv` href, and mock `socket.create_connection` succeeding. The expected output URL must be the direct file URL containing the LAN IP and infohash path segment.
- R14: S14 (`S14_UrlKeyboardInterrupt`) is updated with the same `proc.poll` and `urlopen` mocks. The `proc_mock.terminate.assert_called_once()` assertion is preserved unchanged.
- R15 (renumbered from R13–R14 above): S17 (`S17_QrCode`) and S18 (`S18_QrCodeAbsent`) are updated so `expected_url` reflects the direct file URL, not the directory URL.
- R16: A new test scenario S19 covers the reachability-probe failure path: when `socket.create_connection` raises `OSError`, the exit code is non-zero and nothing about the URL is printed to stdout.

## Acceptance Criteria

- [ ] `./dhtplay --help` does not list `--short-port` in its output; verified by running the command and checking the help text.
- [ ] Running `dhtplay <hash> --url` (with mocked subprocess and urlopen) prints a URL containing the LAN IP and the infohash path segment — not a short redirect port URL. Verified by S13 `test_url_flag_prints_http_url_with_infohash`.
- [ ] When `socket.create_connection` to `(lan_ip, port)` raises `OSError`, the tool exits non-zero and no URL is printed to stdout. Verified by S19.
- [ ] The `subprocess.Popen` call in the `--url` branch passes no `stdout` keyword argument. Verified by S13 `test_url_flag_popen_not_piped`.
- [ ] `python3 test_dhtplay.py` completes with all scenarios passing, including S19.

## Implementation Phases

### Phase 1: Remove redirect server, add reachability probe, update tests

**Scope:** Rework the `--url` branch in `main()` to remove the redirect server and `--short-port` argument, add a post-resolution TCP reachability probe, and update the test suite so all scenarios reflect the new direct-URL behavior.

**Files:**
- `dhtplay` — remove `--short-port` argparse block (lines ~196–199); update `subprocess.Popen` call to not set `stdout`; remove redirect server block (lines ~270–294); add `socket.create_connection` probe after URL resolution; update terminal print and `_render_qr` to use direct file URL; update `KeyboardInterrupt` handler to remove `redir.shutdown()`; remove `from http.server import ...` lazy import
- `test_dhtplay.py` — update S13, S14, S17, S18 with correct mocks (`proc.poll`, `urllib.request.urlopen`, `socket.create_connection`); add S19 reachability-probe failure scenario

**Verification:**
- `python3 test_dhtplay.py` — all scenarios pass
- `./dhtplay --help | grep short-port` — returns no output
- `grep -n "HTTPServer\|BaseHTTPRequestHandler\|redir\|short_port" dhtplay` — returns no matches

**Estimated effort:** Small

## Edge Cases

- `get_lan_ip()` returns `127.0.0.1` (all network interfaces failed): the TCP probe to `127.0.0.1:{port}` succeeds (webtorrent is local), so the tool prints a URL that happens to contain `127.0.0.1` — functionally useless for remote access but not an error; the IP in the URL is self-documenting.
- webtorrent exits during the polling loop (`proc.poll()` returns non-None): existing behavior of printing `webtorrent exited unexpectedly` to stderr and returning 3 is preserved unchanged.
- Directory listing returns no video-extension hrefs within 120 seconds: falls back to directory URL, probe still runs, behavior is unchanged from R7/R8.

## Technical Notes

The `--url` branch currently sets `stdout=subprocess.DEVNULL` on the Popen call (line 235 of `dhtplay`). Test S13 `test_url_flag_popen_not_piped` already asserts this must NOT be present — meaning that test currently fails against the existing code. Removing this kwarg makes the test pass and prevents webtorrent's TUI suppression.

The existing `_find_stream_url` function (lines 119–140) scans subprocess stdout for URLs but is not used in the `--url` path. It should remain untouched; URL discovery continues via HTTP polling against `http://localhost:{port}/webtorrent/{ih_hex}/`.

Reachability probe implementation: `sock = socket.create_connection((lan_ip, port), timeout=2)` inside `try/finally: sock.close()`, wrapped in `except OSError`.

The `tempfile` import inside the `--url` branch stays as a lazy import — webtorrent still needs `--out <tempdir>` to know where to write downloaded files.

## Implementation Notes

## Phase 1: Remove redirect server, add reachability probe, update tests

### Changes made

**dhtplay:**
- Removed `--short-port` argparse block (R1)
- Removed `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` kwargs from Popen call in `--url` branch (R12)
- Removed the entire redirect server block: `from http.server import ...`, `_Redirect` class, `HTTPServer`, daemon thread, `short_url`, `redir.shutdown()` (R2, R3, R4)
- Added TCP reachability probe after URL resolution using `socket.create_connection((lan_ip, args.port), timeout=2)` with a `sock=None` sentinel and `finally` block for cleanup (R8, R9, R10, R11)
- Updated `print` and `_render_qr` calls to use `target_url` (the direct LAN file URL or fallback directory URL) instead of the short redirect URL (R5, R6, R7)

**test_dhtplay.py:**
- S13 (all three methods): added `proc_mock.poll.return_value = None`, `urllib.request.urlopen` mock returning HTML with `.mkv` href, `socket.create_connection` mock (R13)
- S14: same mocks added; `proc_mock.terminate.assert_called_once()` assertion preserved (R14)
- S17: same mocks added; `expected_url` updated to direct file URL `http://192.168.1.100:8888/webtorrent/{IH}/Movie.mkv` (R15)
- S18: same mocks added (R15)
- S19 added: probe raises `OSError`, asserts exit code non-zero and no `http` in stdout (R16)

### Verification results
- `python3 test_dhtplay.py` — 43/43 pass
- `./dhtplay --help | grep short-port` — no output (exit 1)
- `grep -n "HTTPServer|BaseHTTPRequestHandler|redir|short_port" dhtplay` — no matches (exit 1)

## Review

## Verdict

**Verdict:** APPROVE
**Files reviewed:** 2 files changed across 1 phases

All 5 acceptance criteria pass with concrete evidence. The redirect server is fully removed, the Popen call no longer suppresses stdout, the reachability probe correctly gates the URL print behind a TCP check, and all 43 tests pass including the new S19 scenario. No security or convention issues found in the changed files.

### Automated Checks

| Check | Result | Details |
|-------|--------|---------|
| Test suite (python3 test_dhtplay.py) | PASS | 43/43 tests pass including new S19 |
| --short-port absent from --help | PASS | No --short-port in ./dhtplay --help output |
| Redirect server symbols absent from dhtplay | PASS | grep -n 'HTTPServer\|BaseHTTPRequestHandler\|redir\|short_port' dhtplay returns no matches |

### Acceptance Criteria (5/5 passed)

- [x] AC-1: `./dhtplay --help` does not list `--short-port` in its output; verified by running the command and checking the help text. — PASS: ./dhtplay --help output lists only: --trackers, --no-trackers, --name, --dry-run, --webtorrent, --url, --port. No --short-port entry present.
- [x] AC-2: Running `dhtplay <hash> --url` (with mocked subprocess and urlopen) prints a URL containing the LAN IP and the infohash path segment — not a short redirect port URL. Verified by S13 `test_url_flag_prints_http_url_with_infohash`. — PASS: S13 test_url_flag_prints_http_url_with_infohash passes. dhtplay:250 builds file_url = f'http://{lan_ip}:{args.port}{encoded_path}' where lan_ip='192.168.1.100' and encoded_path='/webtorrent/{IH}/Movie.mkv'. Output is '▶  http://192.168.1.100:8888/webtorrent/{IH}/Movie.mkv'.
- [x] AC-3: When `socket.create_connection` to `(lan_ip, port)` raises `OSError`, the tool exits non-zero and no URL is printed to stdout. Verified by S19. — PASS: S19 test_reachability_probe_exits_nonzero passes. dhtplay:263-269: except OSError block prints to stderr and returns 3 before dhtplay:274 (the print f'▶  {target_url}' line). S19 asserts assertNotEqual(rc, 0) and assertNotIn('http', out.getvalue()).
- [x] AC-4: The `subprocess.Popen` call in the `--url` branch passes no `stdout` keyword argument. Verified by S13 `test_url_flag_popen_not_piped`. — PASS: S13 test_url_flag_popen_not_piped passes. dhtplay:227: proc = subprocess.Popen(wt_cmd_http) — no stdout kwarg. Confirmed by git diff: removed stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL from this call.
- [x] AC-5: `python3 test_dhtplay.py` completes with all scenarios passing, including S19. — PASS: python3 test_dhtplay.py output: Ran 43 tests in 0.084s, OK. Final line: 43/43 passed — ALL PASS.

### Code Quality (Refactor Review)

No code quality issues found in changed files.

### Security Assessment (Security Review)

No security issues found in changed files.

### Decisions Made During Implementation

- Exit code 3 reused for the reachability probe failure rather than introducing a new exit code 4 — fits existing 'launch failure' meaning and avoids expanding the exit-code surface for a single-user CLI tool.
- URL discovery in the --url branch continues to use HTTP polling against localhost, not stdout scanning via _find_stream_url — HTTP polling is version-stable; webtorrent TUI output format varies across versions per project memory.
- Socket probe uses sock=None sentinel so the finally block safely skips sock.close() when create_connection raises OSError before assigning the socket, avoiding NameError/AttributeError in the failure path.

## Required Changes

None.

