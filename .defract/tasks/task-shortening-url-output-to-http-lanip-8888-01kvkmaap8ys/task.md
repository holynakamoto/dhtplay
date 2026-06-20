---
defract:
  id: task-shortening-url-output-to-http-lanip-8888-01kvkmaap8ys
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

# Shortening --url output to http://{LANIP}:8888

# Shortening --url output to http://{LANIP}:8888

## What We're Building

When a user runs `dhtplay` with `--url`, the tool currently prints the stream address using port 8000. This task changes the default port to 8888. Users who pass `--port` explicitly keep their chosen port; only the default changes.

## Expected Outcome

- Running `dhtplay <infohash> --url` prints a URL with port 8888 instead of 8000
- Users who pass `--port` explicitly still get their chosen port
- Streaming via the printed URL works correctly (playback is not broken by the change)

## Phase Outcomes

- **Phase 1: Change default port to 8888** — The tool prints `http://{LAN_IP}:8888/0` by default, and the test suite continues to pass with the updated expectation.

## Out of Scope

- Removing the `/0` path segment from the printed URL — that segment is required for the remote player to reach the video file directly rather than an HTML directory listing; removing it would break playback
- Changing how `--port` works beyond updating its default value
- Any changes to VLC launch behavior or webtorrent command arguments
- Modifying `--dry-run` output or any other flag's output format

## Scope Summary

**Size:** 3 requirements, 3 acceptance criteria, 1 implementation phase
**Key decisions:**
- Keep `/0` in the printed URL to preserve streaming correctness; only the port default changes
- Update the corresponding test assertion in S13 so the suite stays green
**Biggest risk:** Minimal — a two-line source change and a one-line test fix with no logic involved.

## Context

The `--url` flag (added in a prior task) launches webtorrent's HTTP streaming server without a local VLC and prints a LAN-accessible URL for remote players. The port is controlled by `--port` (argparse default `8000`). The printed URL is `http://{LAN_IP}:{port}/0` where `/0` is webtorrent's first-file path. The test in S13 (`test_url_flag_prints_http_url`) asserts the string `"8000"` appears in output, so it must be updated alongside the source change.

## Requirements

### Port Default

- R1: The `--port` argument default value is 8888 (currently 8000). (`dhtplay:150`)
- R2: The `--port` help string is updated to reflect the new default, reading `(default: 8888)`. (`dhtplay:153`)

### Tests

- R3: The S13 test assertion that checks for `"8000"` in the `--url` output is updated to check for `"8888"`. (`test_dhtplay.py:406`)

## Acceptance Criteria

- [ ] `./dhtplay <infohash> --url` (no explicit `--port`) launches webtorrent with `-p 8888` and prints `http://<ip>:8888/0`
- [ ] `./dhtplay <infohash> --url --port 9999` still launches webtorrent with `-p 9999` and prints port 9999
- [ ] `python3 test_dhtplay.py` passes all scenarios with zero failures

## Implementation Phases

### Phase 1: Change default port to 8888
**Scope:** Update the `--port` argument default from 8000 to 8888 in the main script, update the help string to match, and fix the S13 test assertion so the suite passes.
**Files:**
- `dhtplay` — line 150: `default=8000` → `default=8888`; line 153: help string `(default: 8000)` → `(default: 8888)`
- `test_dhtplay.py` — line 406: `self.assertIn("8000", output)` → `self.assertIn("8888", output)`
**Verification:**
- Run `python3 test_dhtplay.py`; all scenarios pass
- Run `./dhtplay <any-valid-infohash> --dry-run` to confirm unrelated flags are unaffected
- Inspect `./dhtplay --help` output and confirm `--port` shows `(default: 8888)`
**Estimated effort:** Small

## Edge Cases

- `--port` explicit override: verified by the second acceptance criterion — the default change must not affect explicit port values
- `--url` help text: `./dhtplay --help` must reflect the new default so users are not misled

## Technical Notes

The change is confined to two files and three lines total. No runtime logic changes — only the argparse default and a test assertion.

The `/0` path in the URL is intentionally preserved. webtorrent's HTTP server serves a directory listing at `/` and the first file at `/0`; a URL without `/0` would open a browser listing rather than the stream in a remote player like VLC.

## Implementation Notes

## Phase 1: Change default port to 8888

### Changes Made

**`dhtplay` (lines 150, 152):**
- `default=8000` → `default=8888`
- help string `(default: 8000)` → `(default: 8888)`

**`test_dhtplay.py` (line 406):**
- `self.assertIn("8000", output)` → `self.assertIn("8888", output)`

### Test Results

39/39 tests pass. No deviations from the plan.

## Review

## Verdict

**Verdict:** APPROVE
**Files reviewed:** 2 files changed across 1 phases

All three acceptance criteria pass. The port default was changed from 8000 to 8888 in both the argparse definition and help string, the S13 test assertion was updated to match, and the full 39-test suite passes with zero failures.

### Automated Checks

| Check | Result | Details |
|-------|--------|---------|
| Test suite | PASS | 39/39 pass — python3 test_dhtplay.py ALL PASS |

### Acceptance Criteria (3/3 passed)

- [x] AC-1: `./dhtplay <infohash> --url` (no explicit `--port`) launches webtorrent with `-p 8888` and prints `http://<ip>:8888/0` — PASS: dhtplay:150 default=8888; dhtplay:185 wt_cmd_http uses str(args.port); dhtplay:186 prints f'http://{lan_ip}:{args.port}/0'; S13 test_url_flag_prints_http_url asserts '8888' at test_dhtplay.py:406 and passes
- [x] AC-2: `./dhtplay <infohash> --url --port 9999` still launches webtorrent with `-p 9999` and prints port 9999 — PASS: argparse parses --port into args.port; dhtplay:185-186 use args.port for both Popen args and printed URL; S15 test_port_value_in_popen_args confirms --port 9999 reaches Popen args (test passes)
- [x] AC-3: `python3 test_dhtplay.py` passes all scenarios with zero failures — PASS: python3 test_dhtplay.py output: Ran 39 tests in 0.057s OK — ALL PASS

### Code Quality (Refactor Review)

No code quality issues found in changed files.

### Security Assessment (Security Review)

No security issues found in changed files.

### Decisions Made During Implementation

- Keep /0 path segment in the printed URL; change only the port default from 8000 to 8888 — removing /0 would cause webtorrent to serve an HTML directory listing rather than the video stream

## Required Changes

None.

## Release

## Release Notes

### What was built
- Changed the `--port` argument default from 8000 to 8888 in the `dhtplay` CLI tool
- Updated the argparse help string to read `(default: 8888)` to match the new default
- Updated the S13 test assertion in `test_dhtplay.py` to check for `"8888"` instead of `"8000"`
- Preserved the `/0` path segment in the printed URL to maintain streaming correctness
- Explicit `--port` overrides continue to work correctly at user-specified ports

### Key decisions
- Keep `/0` path segment in the printed URL; change only the port default from 8000 to 8888 — removing `/0` would cause webtorrent to serve an HTML directory listing rather than the video stream

### Changes by phase
- **Phase 1: Change default port to 8888** — Updated `--port` argparse default from 8000 to 8888 in `dhtplay` (lines 150, 152) and updated S13 test assertion in `test_dhtplay.py` (line 406). All 39 tests pass.

## Verification

### Production Build
PASS — Python syntax check and module load passed (no compilation step; single-script project).

### Release Checklist
- [x] Approved review exists — reviewed and approved at 2026-06-20T23:08:47Z (3/3 AC passed, 39/39 tests passed)
- [x] Production build passes — `python3 -m py_compile dhtplay` and module load both PASS
- [x] Code committed and pushed — commit `8880725` pushed to `origin/feature/task-shortening-url-output-to-http-lanip-8888-01kvkmaap8ys`
- [x] Release notes prepared
- [x] Stage content updated
- [x] Completion event logged

