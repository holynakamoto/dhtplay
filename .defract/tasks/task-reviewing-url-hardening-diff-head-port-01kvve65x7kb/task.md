---
defract:
  id: task-reviewing-url-hardening-diff-head-port-01kvve65x7kb
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

# Simplify --url output: drop redirect server, QR-encode direct file URL, add LAN reachability probe

## What We're Building

The `--url` flag currently hands the user a short redirect URL that bounces through a locally-running redirect server. The review session concluded that this redirect hop is unnecessary (QR codes make URL length irrelevant) and is itself a suspect for remote VLC playback failures. This task removes the redirect server entirely, gives VLC and the QR code the direct long file URL from webtorrent's streaming server, and adds a LAN reachability probe so the tool fails fast with a clear error instead of printing a URL that cannot be reached.

## Expected Outcome

- Running `dhtplay <hash> --url` outputs and QR-encodes the direct LAN-accessible file URL, with no redirect hop in the path
- If webtorrent's streaming server cannot be reached from the machine's LAN IP (bound to localhost only), the tool exits with an error before printing anything to the user
- The `--short-port` CLI argument is removed; the tool no longer starts a secondary redirect server
- Tests are updated to reflect the direct URL format, the removed redirect-server tests are dropped, and a new test covers the reachability-probe failure path

## Out of Scope

- The zero-payload-bytes problem (webtorrent stalling mid-download for some magnets) — this is a swarm health issue, not a code defect, tracked separately
- The WebTorrent/aria2 hybrid fallback — a separate follow-up task
- Changes to how webtorrent-cli is discovered, launched, or how trackers are configured
