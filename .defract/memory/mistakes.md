# Mistake Patterns

## Mistakes

- [01KVKPEA7Q1GV798W4DSN3C4F4] **- **Tests that mock subprocess but don't patch background-thread helpers will...** -- - **Tests that mock subprocess but don't patch background-thread helpers will block for the full queue timeout** -- MagicMock's default `__iter__` yields nothing; the daemon reader thread exits immediately without putting anything in the queue, so the main thread waits the full timeout (30 s) before falling back. Tests that do not exercise the URL-scanning path must patch `_find_stream_url` (and `_render_qr`) directly to return immediately. Rule: any test that exercises code containing a `q.get(timeout=N)` must either provide real data through the queue or patch the function that owns it. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.7]. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.7]
- [01KVKPE61DQ8HW0PHXQF5DDJHD] **- **Hardcoding a subprocess output path (e** -- - **Hardcoding a subprocess output path (e.g. /0) causes silent breakage when the external tool updates** -- dhtplay hardcoded `/0` as the webtorrent-cli stream path; webtorrent later changed to serving at `/filename.ext`, making every `--url` invocation a dead link. The fix was to read the actual URL from webtorrent's stdout rather than assuming a path. Rule: whenever consuming an external tool's output format, either read it dynamically or match on a stable structural anchor (like a port number), never a version-specific string. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.7]. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.7]

## Anti-Patterns


