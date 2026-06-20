---
defract:
  id: task-stream-to-mobile-vlc-via-url-no-local-01kvkkcyrteg
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

# Stream to mobile VLC via URL, no local VLC

# Stream to mobile VLC via URL, no local VLC

## What We're Building

When a user runs `dhtplay` with the `--url` flag, the tool currently also opens VLC on the local machine — defeating the purpose of remote streaming. This task removes the local VLC launch from the `--url` path so the tool only runs the HTTP streaming server, and updates the printed URL to point directly to the first playable file so mobile VLC can open it without navigating a file listing.

## Expected Outcome

- Running `dhtplay <infohash> --url` no longer opens VLC on the local machine
- The printed URL points directly to the first file stream (e.g. ending in `/0`) rather than the root `/` listing
- Mobile VLC's "Open Network Stream" can play the URL directly without extra steps
- The `--url` help text accurately describes the new behavior (HTTP-only, no local player)

## Phase Outcomes

- **Phase 1: Fix the --url streaming path** — Users running `dhtplay --url` get a URL they can paste directly into mobile VLC and play immediately, without the local machine also opening a media player.

## Out of Scope

- Letting the user choose which file index to stream when a torrent contains multiple files
- Any changes to the default `dhtplay` behavior (without `--url`)
- Auto-discovery or mDNS broadcasting of the stream URL to nearby devices

## Scope Summary

**Size:** 4 requirements, 6 acceptance criteria, 1 implementation phase
**Key decisions:**
- Hardcode `/0` as the file index path rather than parsing webtorrent's stdout for the actual filename — simpler and sufficient for the single-file use case
- Remove `--vlc` from the webtorrent command in the `--url` branch only; all non-`--url` behavior is untouched
**Biggest risk:** Webtorrent's HTTP server path format for `/0` should match what webtorrent-cli actually serves — worth verifying against a live torrent since the unit tests cannot confirm the server-side path convention.

## Context

The `--url` flag is intended for remote streaming: the user runs the tool on one machine and plays the stream on another device such as mobile VLC. Currently the `--url` branch in `main()` builds `wt_cmd_http` with `--vlc` included (line 185 of `dhtplay`), which causes webtorrent to open VLC locally as well. The printed URL also points to the root `/` listing rather than a specific file, requiring the remote user to navigate the listing before playback begins.

The fix is surgical: remove `--vlc` from the command list in the `--url` branch, update the printed URL from `/{port}/` to `/{port}/0`, and update the `--url` help text. Tests S13 and S14 cover the `--url` path and require corresponding updates.

## Requirements

### Behavior

- R1: When `--url` is passed, webtorrent is launched without the `--vlc` flag so no local media player opens.
- R2: The URL printed to stdout ends with `/0`, pointing directly to the first file served by the HTTP streaming server (e.g. `http://192.168.1.100:8000/0`).
- R3: All existing behavior when `--url` is NOT passed remains unchanged — webtorrent still receives `--vlc` on the default path.

### Documentation

- R4: The `--url` argument's help text no longer claims VLC opens locally; it describes HTTP-only streaming for remote use.

## Acceptance Criteria

- [ ] Running `dhtplay <infohash> --url` calls `subprocess.Popen` with a command that does NOT contain `--vlc`; verified by inspecting `popen_mock.call_args` in S13.
- [ ] The URL printed to stdout by `dhtplay <infohash> --url` ends with `/0` (e.g. `http://192.168.1.100:8000/0`); verified by updated S13 assertion.
- [ ] Running `dhtplay <infohash>` (without `--url`) still calls `subprocess.Popen` with `--vlc` in the args; verified by S11 tests remaining unchanged and passing.
- [ ] A new test assertion in S13 (or a new S17 scenario) asserts that `--vlc` is absent from the Popen call args when `--url` is active.
- [ ] `./dhtplay --help` output for `--url` contains no reference to VLC opening locally; verified by `./dhtplay --help | grep -A3 '\-\-url'`.
- [ ] `python3 test_dhtplay.py` exits 0 with all tests passing.

## Implementation Phases

### Phase 1: Fix the --url streaming path
**Scope:** Remove `--vlc` from the webtorrent command used in the `--url` branch, update the printed URL to include `/0`, update the `--url` help text, and update S13 to match the corrected behavior.
**Files:**
- `dhtplay` — remove `--vlc` from `wt_cmd_http` (line 185); change printed URL suffix from `/` to `/0` (line 186); update `--url` help string (lines 143–145)
- `test_dhtplay.py` — update `S13_UrlFlag.test_url_flag_prints_http_url` to assert the output contains `/0`; add `test_url_flag_no_vlc` asserting `--vlc` is absent from Popen call args when `--url` is passed
**Verification:**
- [ ] `python3 test_dhtplay.py` exits 0 with all scenarios passing
- [ ] `grep -- '--vlc' dhtplay` returns only the non-`--url` command line (the `wt_cmd` list, currently line 181), confirming `--vlc` is absent from the `--url` branch
- [ ] `./dhtplay --help | grep -A3 '\-\-url'` does not contain "VLC also opens locally"
**Estimated effort:** Small

## Edge Cases

- Multi-file torrent: the `/0` path returns the first file only; other files at `/1`, `/2`, etc. are not addressed — file selection is out of scope for this task.
- `--url --port 9999`: the printed URL should be `http://<ip>:9999/0`; the port propagation to both the Popen args and the printed URL is covered by the existing S15 test pattern.
- `--url` combined with `--dry-run`: `--dry-run` exits at line 167 before the `--url` branch at line 183 is reached — behavior is unchanged and requires no new handling.

## Technical Notes

The `--url` branch in `main()` (lines 183–197 of `dhtplay`) currently builds `wt_cmd_http` with the same flags as the default `wt_cmd`, including `--vlc`. The fix is to omit `--vlc` from that list only. No threading, no stdout capture, and no changes to `get_lan_ip()` are required.

The project profile notes a `_find_stream_url` function that was intended to parse webtorrent's stdout for the actual filename URL — this function does not appear in the current file. Appending `/0` to the root URL is the correct approach per the approved intent check and avoids stdout capture complexity.

The current `--url` help string (lines 143–145) reads: "print a remote-accessible stream URL and start the HTTP server (VLC also opens locally; open the printed URL on another machine via Media → Open Network Stream)". The replacement should convey that only the HTTP server starts and the URL points directly to the first stream file.

## Implementation Notes

## Phase 1: Fix the --url streaming path

**Files changed:**
- `dhtplay` — removed `--vlc` from `wt_cmd_http`; changed printed URL from `/{port}/` to `/{port}/0`; updated `--url` help text to "start the HTTP streaming server only (no local player) and print a URL pointing directly to the first file"
- `test_dhtplay.py` — updated `S13.test_url_flag_prints_http_url` to assert `/0` in the printed URL; added `S13.test_url_flag_no_vlc` asserting `--vlc` is absent from Popen call args when `--url` is active

**Test results:** 39/39 passed (1 new test added)

**Verification:**
- `grep -- '--vlc' dhtplay` returns only the `wt_cmd` line (non-`--url` branch) — confirmed
- `./dhtplay --help | grep -A3 '\-\-url'` shows no mention of "VLC also opens locally" — confirmed

## Review

## Verdict

**Verdict:** APPROVE
**Files reviewed:** 2 files changed across 1 phases

All 6 acceptance criteria pass. The --url branch omits --vlc from the webtorrent command, the printed URL ends with /0 for direct mobile playback, the non-url default path is untouched, and the help text no longer references local VLC. 39/39 tests pass including the new no-vlc assertion.

### Automated Checks

| Check | Result | Details |
|-------|--------|---------|
| Test suite | PASS | 39/39 passed (python3 test_dhtplay.py) |

### Acceptance Criteria (6/6 passed)

- [x] AC-1: Running `dhtplay <infohash> --url` calls `subprocess.Popen` with a command that does NOT contain `--vlc`; verified by inspecting `popen_mock.call_args` in S13. — PASS: dhtplay:185 — wt_cmd_http = [wt, magnet, "-p", str(args.port)] contains no --vlc. S13.test_url_flag_no_vlc at test_dhtplay.py:423 asserts assertNotIn("--vlc", call_args) and passes.
- [x] AC-2: The URL printed to stdout by `dhtplay <infohash> --url` ends with `/0` (e.g. `http://192.168.1.100:8000/0`); verified by updated S13 assertion. — PASS: dhtplay:186 — print(f"▶  http://{lan_ip}:{args.port}/0"). S13.test_url_flag_prints_http_url at test_dhtplay.py:407 asserts assertIn("/0", output) and passes.
- [x] AC-3: Running `dhtplay <infohash>` (without `--url`) still calls `subprocess.Popen` with `--vlc` in the args; verified by S11 tests remaining unchanged and passing. — PASS: dhtplay:181 — wt_cmd = [wt, magnet, "--vlc", "-p", str(args.port)]. grep '--vlc' dhtplay returns exactly this one line. S11.test_popen_called_with_magnet at test_dhtplay.py:334 asserts call_args[2] == "--vlc" and passes.
- [x] AC-4: A new test assertion in S13 (or a new S17 scenario) asserts that `--vlc` is absent from the Popen call args when `--url` is active. — PASS: test_dhtplay.py:409-423 — S13.test_url_flag_no_vlc is a new test method that patches Popen, calls main with --url, then asserts assertNotIn("--vlc", popen_mock.call_args[0][0]). Test passes.
- [x] AC-5: `./dhtplay --help` output for `--url` contains no reference to VLC opening locally; verified by `./dhtplay --help | grep -A3 '\-\-url'`. — PASS: dhtplay:144-146 — help text reads "start the HTTP streaming server only (no local player) and print a URL pointing directly to the first file; open it on another device via Media → Open Network Stream". ./dhtplay --help | grep -A3 '\-\-url' shows no mention of "VLC also opens locally".
- [x] AC-6: `python3 test_dhtplay.py` exits 0 with all tests passing. — PASS: python3 test_dhtplay.py output: Ran 39 tests in 0.055s, OK, RESULTS: 39/39 passed — ALL PASS. Exit code 0.

### Code Quality (Refactor Review)

No code quality issues found in changed files.

### Security Assessment (Security Review)

No security issues found in changed files.

### Decisions Made During Implementation

- Hardcode /0 as the file index path rather than parsing webtorrent stdout — simpler, sufficient for the single-file common case, and consistent with webtorrent-cli's numeric index path convention.

## Required Changes

None.

## Release

## Release Notes

### What was built
- Removed `--vlc` from the webtorrent command in the `--url` branch so that running `dhtplay <infohash> --url` no longer opens VLC on the local machine
- Updated the printed URL suffix from `/` to `/0` so mobile VLC can open the stream directly without navigating a file listing
- Updated the `--url` argument help text to accurately describe HTTP-only streaming with no local player
- Added a new test (`S13.test_url_flag_no_vlc`) verifying `--vlc` is absent from Popen args when `--url` is active

### Key decisions
- Hardcode `/0` as the file index path rather than parsing webtorrent's stdout for the actual filename — simpler, sufficient for the single-file common case, and consistent with webtorrent-cli's numeric index path convention

### Changes by phase
- **Phase 1: Fix the --url streaming path** — Removed `--vlc` from `wt_cmd_http` in `dhtplay`; updated printed URL from `/{port}/` to `/{port}/0`; updated `--url` help text; added S13.test_url_flag_no_vlc; updated S13.test_url_flag_prints_http_url to assert `/0`. 39/39 tests pass.

## Verification

- Production build (py_compile): PASS
- Test suite: 39/39 passed
- `grep -- '--vlc' dhtplay` returns only the `wt_cmd` line (non-`--url` branch)
- `./dhtplay --help | grep -A3 '\-\-url'` contains no reference to local VLC
- Branch pushed to origin: `feature/task-stream-to-mobile-vlc-via-url-no-local-01kvkkcyrteg`
- Commit: `c58fa2a feat(task-stream-to-mobile-vlc-via-url-no-local-01kvkkcyrteg): phase 1 — Fix the --url streaming path`

