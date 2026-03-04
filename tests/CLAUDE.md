# Tests

- Never use `time.sleep()` in tests. Instead, modify timestamps or other values directly (e.g., read a log, bump `completed_at`, write it back).
- Prefer the `recording_console` fixture over `capsys`/`capfd` for capturing output. It captures both Rich console output and Python logging output (via `RichHandler`).
