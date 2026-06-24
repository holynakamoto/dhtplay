---
defract:
  id: task-url-stream-not-playing-shortening-the-01kvvgrjj8kz
  type: bug
  status: active
  stage: release
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

# Fix --url stream: resolve actual file URL from webtorrent stdout

# Fix --url stream: resolve actual file URL from webtorrent stdout

## What We're Building

The `--url` mode is broken: it hardcodes a path format that webtorrent no longer uses, so it either times out after two minutes or hands the viewer a dead link. We are replacing the broken directory-poll approach with one that reads the real streaming URL directly from webtorrent's own output, so the correct playable link is printed immediately and reliably.

## Expected Outcome

- Running `dhtplay <infohash> --url` prints a working HTTP stream URL within seconds of webtorrent finding metadata, instead of waiting up to two minutes and then printing a dead link
- The printed URL can be opened in VLC (or any media player) on another device and actually plays the file
- If the streaming server is not reachable after a reasonable wait, the command exits with a clear error message rather than printing a URL that will not work
- The fix works regardless of which version of webtorrent-cli is installed, since it reads what webtorrent actually announces rather than guessing a path

## Phase Outcomes

- **Phase 1: Replace HTTP polling with stdout URL scanning** — The `--url` command correctly reads the stream URL that webtorrent announces on startup and prints it immediately instead of waiting up to two minutes. The command exits with a clear error if no URL appears within 30 seconds. Existing tests are updated to verify the new behavior.

## Out of Scope

- Shortening the printed URL (e.g. a redirect server or QR-only flow) — that is a separate enhancement and should come after the streaming URL is reliable
- Changes to the default VLC playback mode (no `--url` flag)
- Any UI or configuration changes to port selection or tracker behaviour

## Scope Summary

**Size:** 8 requirements, 7 acceptance criteria, 1 implementation phase
**Key decisions:**
- Use the already-written `_find_stream_url` function rather than introducing new URL-scanning logic — it exists but is not yet called in the `--url` branch
- Remove `--quiet` from the webtorrent command and pipe stdout so the URL announcement reaches `_find_stream_url`
- Replace the 120-second HTTP polling loop entirely — no hybrid approach
**Biggest risk:** webtorrent may emit the streaming URL on stderr rather than stdout in some installations; if so, the 30-second timeout fires and the command exits with an error rather than hanging.

## Context

The `_find_stream_url` function (lines 119–140 of `dhtplay`) was added in a prior task and implements the correct approach: a daemon thread drains `proc.stdout` line-by-line while the main thread waits on a `queue.Queue` with a timeout. It uses a port-anchored regex (`https?://\S*{port}\S*`) that is stable across webtorrent-cli versions. The function was never connected to the `--url` branch in `main()`. Instead, the `--url` branch uses `--quiet` (which suppresses stdout entirely) and polls an HTTP directory listing at a path that webtorrent-cli no longer serves. Tests S13–S19 in `test_dhtplay.py` all mock `urllib.request.urlopen` because they were written for the old polling approach; they need to be rewritten to mock `proc.stdout` as a string iterator.

## Requirements

### Startup behavior

- R1: The `--url` branch launches webtorrent with `stdout=subprocess.PIPE, text=True` on the `subprocess.Popen` call so that `_find_stream_url` can read from `proc.stdout`.
- R2: `--quiet` is removed from the webtorrent command arguments so the streaming URL announcement is not suppressed.

### URL resolution

- R3: After launching webtorrent, `_find_stream_url(proc, args.port, timeout=30)` is called to obtain the streaming URL from webtorrent's stdout. The existing function at lines 119–140 is used unchanged.
- R4: The host in the returned URL (`localhost` or `127.0.0.1`) is replaced with the LAN IP from `get_lan_ip()` so the printed URL is reachable from another device. Use `re.sub(r'https?://(?:localhost|127\\.0\\.0\\.1)', f'http://{lan_ip}', raw_url)`.
- R5: If `_find_stream_url` returns `None` (timeout or early process exit), the command prints a descriptive error to stderr and exits with code 3. No URL is printed to stdout.

### Test coverage

- R6: The mock setup in test scenarios S13–S19 is updated to supply `proc_mock.stdout = iter(["http://localhost:8888/File.mkv\n"])`, replacing the `urlopen` mock pattern that tested the old polling approach.
- R7: `S13.test_url_flag_popen_not_piped` is replaced with a test verifying that `--quiet` is absent from the Popen call argument list.
- R8: A test verifies that when `proc.stdout` is an empty iterator (no URL-matching line), the command exits non-zero and prints nothing to stdout.

## Acceptance Criteria

- [ ] `dhtplay <infohash> --url` exits 0 and prints a line containing `http://<lan-ip>:8888/` when webtorrent announces a URL on stdout; verified by S13 passing
- [ ] The printed URL contains the LAN IP from `get_lan_ip()`, not `localhost` or `127.0.0.1`; verified by `S13.test_url_flag_prints_http_url_with_lan_ip`
- [ ] When `proc.stdout` yields no URL-matching line, the command exits non-zero and stdout is empty; verified by the new timeout test (R8)
- [ ] The `--url` Popen call does not include `--quiet` in its argument list; verified by the replacement S13 test (R7)
- [ ] `_find_stream_url` is called with the subprocess handle and `args.port`; no new URL-scanning logic is introduced; verified by reading `dhtplay` lines 221–270 after the change
- [ ] `grep -n "urlopen" dhtplay` returns no results — the HTTP polling loop is fully removed
- [ ] `python3 test_dhtplay.py` exits 0 with all scenarios passing after the change

## Implementation Phases

### Phase 1: Replace HTTP polling with stdout URL scanning
**Scope:** Remove the 120-second `urlopen` polling loop from the `--url` branch and replace it with a call to `_find_stream_url`. Update the webtorrent command to pipe stdout and remove `--quiet`. Rewrite the five affected test scenarios (S13–S19) to mock `proc.stdout` instead of `urlopen`.
**Files:**
- `dhtplay` — in the `if args.url:` block: add `stdout=subprocess.PIPE, text=True` to `Popen`; remove `--quiet` from `wt_cmd_http`; delete the `while time.time() < deadline` loop and replace with `_find_stream_url(proc, args.port, timeout=30)` + host substitution via `re.sub`; handle `None` return with error exit
- `test_dhtplay.py` — in S13–S19: swap `urlopen` mock setup for `proc_mock.stdout = iter([...])` with a simulated URL line; replace `test_url_flag_popen_not_piped` with `test_url_flag_no_quiet`; add an empty-iterator test for the timeout path
**Verification:**
- `python3 test_dhtplay.py` exits 0 with all scenarios passing
- `grep -n "urlopen" dhtplay` returns no results
- `grep -n "_find_stream_url" dhtplay` shows exactly one call site inside the `if args.url:` block
- `grep -n "\-\-quiet" dhtplay` returns no results
**Estimated effort:** Small

## Edge Cases

- Timeout before URL appears: `_find_stream_url` returns `None`; command exits 3 with message "timed out waiting for stream URL"
- webtorrent exits before announcing a URL: the reader thread drains and exits; `queue.get` times out; same `None` path applies; message "webtorrent exited unexpectedly" if `proc.poll()` is non-None
- URL path contains percent-encoded characters: `_find_stream_url` captures `\S*` (non-whitespace), so encoding is preserved unchanged
- LAN IP unavailable (`get_lan_ip()` returns `127.0.0.1`): the printed URL contains `127.0.0.1`, which plays locally but not remotely — acceptable fallback matching existing behaviour

## Technical Notes

The host substitution should cover both loopback forms since webtorrent-cli versions differ in which they emit:

```python
target_url = re.sub(r'https?://(?:localhost|127\.0\.0\.1)', f'http://{lan_ip}', raw_url)
```

The reachability probe (`socket.create_connection`) that follows URL resolution is retained unchanged — it is an independent safety gate already tested by S19.

`_find_stream_url` continues draining `proc.stdout` after the first match (the `matched` flag stops queue writes but the thread reads to exhaustion). This prevents pipe-buffer deadlock for the lifetime of the webtorrent process. No change to the function is needed.

Test scenarios that currently patch `urllib.request.urlopen` (S13–S19) will error immediately after the fix since `urlopen` is no longer called. The correct rewrite pattern is:

```python
proc_mock.stdout = iter(["http://localhost:8888/Movie.mkv\n"])
```

This matches the `text=True` expectation in `_find_stream_url` (which iterates `proc.stdout` as strings).

## Implementation Notes

## Phase 1: Replace HTTP polling with stdout URL scanning

### Changes

**`dhtplay`**
- Removed unused imports: `import time`, `import urllib.request`, `import urllib.parse`
- Rewrote `if args.url:` block: removed `import tempfile`, `--quiet`, `--out out_dir`, `--keep-seeding` stays, added `stdout=subprocess.PIPE, text=True` to Popen
- Removed the 120-second `urlopen` polling loop entirely
- Added `_find_stream_url(proc, args.port, timeout=30)` call; handles `None` return with stderr message and exit 3
- Added `re.sub(r'https?://(?:localhost|127\.0\.0\.1)', f'http://{lan_ip}', raw_url)` for LAN IP substitution

**`test_dhtplay.py`**
- S13: renamed `test_url_flag_prints_http_url_with_infohash` → `test_url_flag_prints_http_url_with_lan_ip`; removed urlopen mock; added `proc_mock.stdout = iter([...])`
- S13: updated `test_url_flag_no_vlc` — same mock pattern change
- S13: replaced `test_url_flag_popen_not_piped` with `test_url_flag_no_quiet` (verifies `--quiet` absent from Popen args)
- S13: added `test_url_flag_timeout_exits_nonzero_no_stdout` (patches `_find_stream_url` to return `None`; verifies exit non-zero, stdout empty)
- S14, S17, S18, S19: removed urlopen mocks; added `proc_mock.stdout = iter(["http://localhost:8888/Movie.mkv\n"])`
- S17: updated `expected_url` from infohash-based path to `http://192.168.1.100:8888/Movie.mkv`

### Result
44/44 tests passing (up from 43 — one new test added). All verification greps clean.

## Review

## Verdict

**Verdict:** APPROVE
**Files reviewed:** 2 files changed across 1 phases

All 7 acceptance criteria pass. The HTTP polling loop is fully removed, the --url branch correctly pipes webtorrent stdout and calls _find_stream_url, LAN IP substitution is applied, and the timeout path exits non-zero with no stdout output. 44/44 tests pass.

### Automated Checks

| Check | Result | Details |
|-------|--------|---------|
| Test suite | PASS | 44/44 passed — ALL PASS |

### Acceptance Criteria (7/7 passed)

- [x] AC-1: `dhtplay <infohash> --url` exits 0 and prints a line containing `http://<lan-ip>:8888/` when webtorrent announces a URL on stdout; verified by S13 passing — PASS: S13_UrlFlag.test_url_flag_prints_http_url_with_lan_ip passes. dhtplay:218-258: Popen launched with stdout=PIPE+text=True, _find_stream_url reads URL, re.sub replaces host, print outputs the URL, returns 0.
- [x] AC-2: The printed URL contains the LAN IP from `get_lan_ip()`, not `localhost` or `127.0.0.1`; verified by `S13.test_url_flag_prints_http_url_with_lan_ip` — PASS: dhtplay:235: re.sub(r'https?://(?:localhost|127\.0\.0\.1)', f'http://{lan_ip}', raw_url). Test mocks get_lan_ip returning '192.168.1.100' and asserts '192.168.1.100' in output and 'localhost' not in output — passes.
- [x] AC-3: When `proc.stdout` yields no URL-matching line, the command exits non-zero and stdout is empty; verified by the new timeout test (R8) — PASS: S13_UrlFlag.test_url_flag_timeout_exits_nonzero_no_stdout passes. dhtplay:228-233: when _find_stream_url returns None, prints error to stderr and returns 3. Test patches _find_stream_url to return None, asserts rc != 0 and out.getvalue() == ''.
- [x] AC-4: The `--url` Popen call does not include `--quiet` in its argument list; verified by the replacement S13 test (R7) — PASS: S13_UrlFlag.test_url_flag_no_quiet passes. dhtplay:219: wt_cmd_http = [wt, magnet, '-p', str(args.port), '--keep-seeding'] — no --quiet present. Test captures all Popen cmd args and asserts '--quiet' not in captured_args.
- [x] AC-5: `_find_stream_url` is called with the subprocess handle and `args.port`; no new URL-scanning logic is introduced; verified by reading `dhtplay` lines 221–270 after the change — PASS: dhtplay:227: raw_url = _find_stream_url(proc, args.port, timeout=30). grep shows exactly two lines: line 116 (definition) and line 227 (call site inside if args.url: block). No new URL-scanning logic introduced.
- [x] AC-6: `grep -n "urlopen" dhtplay` returns no results — the HTTP polling loop is fully removed — PASS: grep -n 'urlopen' dhtplay returns exit code 1 with no output. The polling loop and urllib imports are fully removed.
- [x] AC-7: `python3 test_dhtplay.py` exits 0 with all scenarios passing after the change — PASS: python3 test_dhtplay.py: 44/44 passed — ALL PASS. Exit code 0.

### Code Quality (Refactor Review)

No code quality issues found in changed files.

### Security Assessment (Security Review)

No security issues found in changed files.

### Decisions Made During Implementation

- Use existing _find_stream_url function unchanged — wire it in, don't rewrite it
- Remove --quiet from the webtorrent command and pipe stdout so the URL announcement reaches _find_stream_url
- Patch _find_stream_url in timeout test rather than using iter([]) with the real function to avoid blocking for the full 30s timeout

## Required Changes

None.

## Release

## Release Notes

### What was built
- Fixed `--url` mode by replacing a 120-second HTTP polling loop with direct stdout URL scanning from webtorrent's process output
- Connected the existing `_find_stream_url` function (previously written but unused) to the `--url` launch path in `main()`
- Removed `--quiet` from the webtorrent command and added `stdout=subprocess.PIPE, text=True` to capture URL announcements
- Added LAN IP substitution via `re.sub` so the printed URL is reachable from other devices on the network
- Updated 7 test scenarios (S13–S19) to mock `proc.stdout` as string iterators instead of `urllib.request.urlopen`

### Key decisions
- Use existing `_find_stream_url` function unchanged — wire it in, don't rewrite it
- Remove `--quiet` from the webtorrent command and pipe stdout so the URL announcement reaches `_find_stream_url`
- Patch `_find_stream_url` in timeout test rather than using `iter([])` with the real function to avoid blocking for the full 30s timeout

### Changes by phase
- **Phase 1: Replace HTTP polling with stdout URL scanning** — Removed 120-second `urlopen` polling loop; added `stdout=PIPE+text=True` to Popen; called `_find_stream_url` for real URL; applied LAN IP substitution; rewrote S13–S19 tests with `proc_mock.stdout` iterators. 44/44 tests passing.

## Verification

- Production build: Python single-file script — no compilation step; test suite used as build gate
- Test suite: 44/44 passed — ALL PASS
- Working tree clean at release; implementation committed as `4362d04 feat(task-url-stream-not-playing-shortening-the-01kvvgrjj8kz): phase 1 — Replace HTTP polling with stdout URL scanning`
- Feature branch pushed to `origin/feature/task-url-stream-not-playing-shortening-the-01kvvgrjj8kz`
- Review approved: 2026-06-24 — 7/7 acceptance criteria, all automated checks passed

