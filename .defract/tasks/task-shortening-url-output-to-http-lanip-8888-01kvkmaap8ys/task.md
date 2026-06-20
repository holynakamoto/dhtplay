---
defract:
  id: task-shortening-url-output-to-http-lanip-8888-01kvkmaap8ys
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

# Shortening --url output to http://{LANIP}:8888

## What We're Building

When a user runs `dhtplay` with `--url`, the tool currently prints the stream address as `http://{LAN_IP}:8000/0`. This task changes the default port from 8000 to 8888. The stated goal is `http://{LAN_IP}:8888` with no path segment, but the `/0` at the end is how the player reaches the video file — removing it would serve an HTML directory listing instead of the stream. This intent check surfaces that tradeoff so the builder can confirm whether to keep or drop `/0`.

## Expected Outcome

- Running `dhtplay <infohash> --url` prints a URL with port 8888 instead of 8000
- Users who pass `--port` explicitly still get their chosen port
- Streaming via the printed URL works correctly (playback is not broken by the change)

## Out of Scope

- Changing how `--port` works beyond updating its default value
- Any changes to VLC launch behavior or webtorrent command arguments
- Modifying `--dry-run` output or any other flag's output format
