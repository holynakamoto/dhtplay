---
defract:
  id: task-building-dhtplay-capability-test-matrix-01kvkj9nqz2k
  type: bug
  status: active
  stage: scope
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

## What We're Building

Expand the existing test suite from 12 to 16 scenarios to cover three capabilities that currently have zero test coverage: the `--url` flag, the `--port` flag, and `get_lan_ip()`. Alongside the new tests, fix three known defects — a NameError in `get_lan_ip()` when socket creation fails, an environment-coupled S10 test that breaks on machines without `webtorrent-cli` installed, and dead code (`_find_stream_url`) that is never called and should be removed.

## Expected Outcome

- All 16 test scenarios pass with `python3 test_dhtplay.py` on any machine, regardless of whether `webtorrent-cli` or VLC is installed
- The `--url` flag is covered by a test that verifies the printed URL format and keyboard interrupt handling
- The `--port` flag is covered by a test that verifies the port value reaches the subprocess call
- `get_lan_ip()` is covered by tests for the ipconfig success path, the socket fallback, and the error fallback to 127.0.0.1
- The NameError bug in `get_lan_ip()` is fixed so the socket-error fallback returns 127.0.0.1 cleanly
- Dead code (`_find_stream_url`) is removed, reducing maintenance surface

## Out of Scope

- Adding new CLI features or changing existing user-facing behavior
- End-to-end testing that requires a real `webtorrent-cli` or VLC installation
- CI/CD setup or automated test infrastructure
