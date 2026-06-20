# Project Facts

## Tech Stack


## Conventions

- [01KVKPEDMJ6AP575NEFBFW17AP] **- **Pass text=True to subprocess** -- - **Pass text=True to subprocess.Popen when test mocks supply string iterators for stdout** -- Using `text=True` in `subprocess.Popen` makes `proc.stdout` yield `str` lines, removing the need for a `.decode()` step in the reader and keeping types consistent between production code and test mocks (which typically do `proc_mock.stdout = iter(["line\n"])`). Without `text=True`, the production reader gets bytes while mocks supply strings, causing silent type mismatches. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.5]. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.5]

## Patterns

- [01KVKPE1NBA6D9HVRYERJB0HRB] **- **Use a version-stable anchor (e** -- - **Use a version-stable anchor (e.g. port number) when regex-matching subprocess stdout URLs** -- webtorrent-cli changed its stdout path format across versions (/0 → /filename.ext). The port number is present in any URL the process announces and does not change with version. Pattern: `re.search(r'https?://\S*' + re.escape(str(port)) + r'\S*', line)`. Avoid matching on fixed paths or path prefixes that tie the tool to a specific upstream version. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.6]. [source: task-streaming-to-mobile-vlc-localhost-url-01kvkn6afw76, importance: 0.6]

