---
defract:
  id: task-url-stream-not-playing-shortening-the-01kvvgrjj8kz
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

# Fix --url stream: resolve actual file URL from webtorrent stdout

## What We're Building

The `--url` mode is broken: it hardcodes a path format that webtorrent no longer uses, so it either times out after two minutes or hands the viewer a dead link. We are replacing the broken directory-poll approach with one that reads the real streaming URL directly from webtorrent's own output, so the correct playable link is printed immediately and reliably.

## Expected Outcome

- Running `dhtplay <infohash> --url` prints a working HTTP stream URL within seconds of webtorrent finding metadata, instead of waiting up to two minutes and then printing a dead link
- The printed URL can be opened in VLC (or any media player) on another device and actually plays the file
- If the streaming server is not reachable after a reasonable wait, the command exits with a clear error message rather than printing a URL that will not work
- The fix works regardless of which version of webtorrent-cli is installed, since it reads what webtorrent actually announces rather than guessing a path

## Out of Scope

- Shortening the printed URL (e.g. a redirect server or QR-only flow) — that is a separate enhancement and should come after the streaming URL is reliable
- Changes to the default VLC playback mode (no `--url` flag)
- Any UI or configuration changes to port selection or tracker behaviour
