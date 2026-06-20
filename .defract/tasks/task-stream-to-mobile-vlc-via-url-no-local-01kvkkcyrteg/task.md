---
defract:
  id: task-stream-to-mobile-vlc-via-url-no-local-01kvkkcyrteg
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

# Stream to mobile VLC via URL, no local VLC

## What We're Building

When a user runs `dhtplay` with the `--url` flag, the tool currently also opens VLC on the local machine — defeating the purpose of remote streaming. This task removes the local VLC launch from the `--url` path so the tool only runs the HTTP streaming server, and updates the printed URL to point directly to the first playable file so mobile VLC can open it without navigating a file listing.

## Expected Outcome

- Running `dhtplay <infohash> --url` no longer opens VLC on the local machine
- The printed URL points directly to the first file stream (e.g. ending in `/0`) rather than the root `/` listing
- Mobile VLC's "Open Network Stream" can play the URL directly without extra steps
- The `--url` help text accurately describes the new behavior (HTTP-only, no local player)

## Out of Scope

- Letting the user choose which file index to stream when a torrent contains multiple files
- Any changes to the default `dhtplay` behavior (without `--url`)
- Auto-discovery or mDNS broadcasting of the stream URL to nearby devices
