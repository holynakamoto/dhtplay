# Past Decisions

## Decisions

- [01KVKPDY6D000STXZ1V8RBJXH4] **- **Use daemon thread + queue** -- - **Use daemon thread + queue.Queue for non-blocking subprocess stdout scanning** -- When a subprocess must stay running while the parent reads its stdout, spawn a daemon thread that drains the pipe line-by-line and puts the first match into a queue.Queue. Main thread calls q.get(timeout=N), catching queue.Empty to trigger a fallback. Continuous draining prevents pipe buffer deadlock; daemon flag ensures the thread does not block process exit. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.7]. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.7]

