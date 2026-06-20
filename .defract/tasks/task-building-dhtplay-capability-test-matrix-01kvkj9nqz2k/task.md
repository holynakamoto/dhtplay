---
defract:
  id: task-building-dhtplay-capability-test-matrix-01kvkj9nqz2k
  type: bug
  status: active
  stage: implementation
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

# Building dhtplay capability test matrix

# Building dhtplay capability test matrix

## What We're Building

Expand the existing test suite from 12 to 16 scenarios to cover three capabilities that currently have zero test coverage: the `--url` flag, the `--port` flag, and `get_lan_ip()`. Alongside the new tests, fix three known defects — a NameError in `get_lan_ip()` when socket creation fails, an environment-coupled S10 test that breaks on machines without `webtorrent-cli` installed, and dead code (`_find_stream_url`) that is never called and should be removed.

## Expected Outcome

- All 16 test scenarios pass with `python3 test_dhtplay.py` on any machine, regardless of whether `webtorrent-cli` or VLC is installed
- The `--url` flag is covered by a test that verifies the printed URL format and keyboard interrupt handling
- The `--port` flag is covered by a test that verifies the port value reaches the subprocess call
- `get_lan_ip()` is covered by tests for the ipconfig success path, the socket fallback, and the error fallback to 127.0.0.1
- The NameError bug in `get_lan_ip()` is fixed so the socket-error fallback returns 127.0.0.1 cleanly
- Dead code (`_find_stream_url`) is removed, reducing maintenance surface

## Phase Outcomes

- **Phase 1: Fix defects and add missing test coverage** — Developers running the test suite on any machine see 16 scenarios all passing, including previously untested flag behaviors, and two silent bugs are eliminated from the main script.

## Out of Scope

- Adding new CLI features or changing existing user-facing behavior
- End-to-end testing that requires a real `webtorrent-cli` or VLC installation
- CI/CD setup or automated test infrastructure

## Scope Summary

**Size:** 7 requirements, 9 acceptance criteria, 1 implementation phase
**Key decisions:**
- S10 is refactored to mock environment dependencies so it passes on any machine; the original behavior-under-test (that `find_webtorrent` prefers hardcoded candidates over `which`) is preserved via patching `_executable` and `subprocess.run`
- `_find_stream_url` is removed entirely rather than deprecated — it is unreachable code whose docstring describes behavior that does not exist in the `--url` branch of `main()`
**Biggest risk:** The NameError fix must not alter the happy-path return value of `get_lan_ip()`; a careless restructuring of the try/finally could change behavior when `socket.connect()` succeeds.

## Context

The test suite at `test_dhtplay.py` covers 12 scenarios (S01–S12) exercising infohash parsing, magnet URI construction, dry-run, webtorrent detection, subprocess launch, and CLI smoke tests. Three features in `dhtplay` — `--url`, `--port`, and `get_lan_ip()` — have no corresponding tests.

Two bugs exist in production code: `get_lan_ip()` (lines 101–108 of `dhtplay`) contains a `finally: s.close()` block that executes even when `socket.socket()` raises `OSError` before `s` is bound, causing a NameError that masks the intended `"127.0.0.1"` fallback. S10 at `test_dhtplay.py:289–301` calls `find_webtorrent()` against the real filesystem, making the scenario environment-dependent. `_find_stream_url` (lines 111–137 of `dhtplay`) is dead code: it is never called from `main()` and has no other callers.

## Requirements

### Bug Fixes

- R1: `get_lan_ip()` must return `"127.0.0.1"` cleanly when `socket.socket()` raises `OSError`, without raising a NameError. (`dhtplay` lines 101–108: initialize `s = None` before the try block and guard the `finally` with `if s is not None`.)
- R2: S10 must pass on machines without webtorrent-cli installed. Replace the live `find_webtorrent()` call with mock-based tests that verify the resolution logic (hardcoded candidates tried before `which`) by patching `dhtplay._executable` and `dhtplay.subprocess.run`.
- R3: Remove `_find_stream_url` (lines 111–137 of `dhtplay`) entirely — it is dead code with no callers.

### New Test Scenarios

- R4: Add S13 (`--url` flag prints URL) verifying that `main([IH, "--url"])` prints a line containing `http://` and the port number to stdout and returns exit code 0. Mock `subprocess.Popen`, `find_webtorrent`, and `get_lan_ip`.
- R5: Add S14 (`--url` keyboard interrupt handling) verifying that a `KeyboardInterrupt` raised from `proc.wait()` causes `proc.terminate()` to be called. Use `MagicMock` with a `side_effect` on `.wait()`.
- R6: Add S15 (`--port` flag) verifying that the integer value passed via `--port` appears in the subprocess command list passed to `Popen`. Assert both `-p` and the port string are in `call_args`.
- R7: Add S16 (`get_lan_ip()` unit tests) with three sub-tests: (a) ipconfig returns an IP — function returns that IP; (b) all ipconfig calls fail, socket path succeeds — function returns the socket's address; (c) all ipconfig calls fail and `socket.socket()` raises `OSError` — function returns `"127.0.0.1"` without raising.

## Acceptance Criteria

- [ ] `python3 test_dhtplay.py` reports 16 scenarios all PASS on a machine without webtorrent-cli or VLC installed
- [ ] S13 asserts stdout contains `http://` and the configured port number; no real network calls are made
- [ ] S14 asserts `proc.terminate()` is called exactly once after a `KeyboardInterrupt` from `proc.wait()`
- [ ] S15 asserts the string form of the port value and the `-p` flag both appear in the `Popen` call args list
- [ ] S16(c) asserts `get_lan_ip()` returns `"127.0.0.1"` (not raises `NameError`) when `socket.socket()` raises `OSError`
- [ ] S10 passes without webtorrent-cli installed (behavior-under-test is the resolution logic, not system state)
- [ ] `grep _find_stream_url dhtplay` returns no matches after the change
- [ ] `get_lan_ip()` still returns the correct IP on the happy path (ipconfig succeeds for en0)
- [ ] No test makes a real subprocess, network, or filesystem call; all external I/O is mocked

## Implementation Phases

### Phase 1: Fix defects and add missing test coverage
**Scope:** Apply the three bug fixes to `dhtplay` and add four new test scenarios (S13–S16) to `test_dhtplay.py`, bringing total scenarios from 12 to 16.
**Files:**
- `dhtplay` — fix NameError in `get_lan_ip()` (lines 101–108), remove `_find_stream_url` (lines 111–137)
- `test_dhtplay.py` — refactor S10 (lines 289–301), add S13, S14, S15, S16 class definitions
**Verification:**
- `python3 test_dhtplay.py` exits 0 and prints `16/16 passed — ALL PASS`
- `grep _find_stream_url dhtplay` returns no matches
- S16(c) specifically exercises the formerly-buggy code path and returns `"127.0.0.1"`
- All 16 scenarios pass with webtorrent-cli removed from PATH
**Estimated effort:** Small

## Edge Cases

- `socket.socket()` raises `OSError` before `s` is assigned: the `finally` block must guard against an unbound `s` — this is the exact NameError being fixed
- `proc.wait()` raising `KeyboardInterrupt` in the `--url` branch: `proc.terminate()` must be called and `main()` must return 0 (intended behavior; S14 verifies it)
- Non-standard port values passed via `--port`: they pass through as-is to the subprocess command; no validation is in scope
- S10 on a machine where webtorrent-cli happens to be installed: the refactored test still passes because it tests resolution logic via mocks, not actual filesystem state

## Technical Notes

The NameError in `get_lan_ip()` is subtle: the `except OSError` clause does return `"127.0.0.1"`, but Python runs the `finally` block after the `except` handler and before the return value propagates to the caller. When `socket.socket()` itself raises `OSError`, `s` is never bound, so `s.close()` in `finally` raises `NameError` — replacing the clean return with an exception. Fix: initialize `s = None` before the `try` block and use `if s is not None: s.close()` in `finally`.

S10's existing tests assert that webtorrent-cli is installed on the machine — they are not testing `find_webtorrent()` logic. The refactored S10 should test that hardcoded candidates are preferred over `which`: patch `dhtplay._executable` to return `True` for a known path and assert the function returns that path without calling `which`; patch `dhtplay._executable` to return `False` for all candidates and patch `dhtplay.subprocess.run` to simulate a successful `which` response, asserting the fallback path is returned.

The `_find_stream_url` function uses `proc.stdout` piping and a background thread. Removing it is safe: nothing in `main()` or `test_dhtplay.py` calls it. The `--url` branch in `main()` (lines 211–225) launches webtorrent with `subprocess.Popen` without capturing stdout.

All new tests should follow the established pattern in `test_dhtplay.py`: mock `subprocess.Popen`, `find_webtorrent`, and any other I/O; capture output via `io.StringIO` and `contextlib.redirect_stdout`/`redirect_stderr`.

## Implementation Notes

## Phase 1: Fix defects and add missing test coverage

### Files changed

**`dhtplay`**
- Fixed `get_lan_ip()` NameError: initialized `s = None` before the try block; guarded `finally` with `if s is not None: s.close()`. The happy path (ipconfig or socket succeeds) is unchanged.
- Removed `_find_stream_url` (was lines 111–137) entirely — no callers existed.
- Removed `import threading` (was only used by `_find_stream_url`).

**`test_dhtplay.py`**
- Refactored S10: replaced environment-coupled live `find_webtorrent()` calls with two mock-based tests verifying the resolution logic (hardcoded candidates preferred over `which` fallback).
- Added S13 (`--url` flag): asserts stdout contains `http://` and `8000` (default port), exit code 0. Mocks Popen, find_webtorrent, get_lan_ip.
- Added S14 (`--url` keyboard interrupt): asserts `proc.terminate()` called exactly once after `KeyboardInterrupt` from `proc.wait()`, exit code 0.
- Added S15 (`--port` flag): asserts both `-p` and `"9999"` appear in the Popen call args list.
- Added S16 (`get_lan_ip()` unit tests): three sub-tests covering ipconfig success, socket fallback, and OSError fallback to `"127.0.0.1"` — the last specifically exercises the formerly-buggy code path.

### Test results
38/38 tests pass across 16 scenario classes (S01–S16). No real subprocess, network, or filesystem calls are made by any test.
