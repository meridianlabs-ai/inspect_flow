# Tests

- Never use `time.sleep()` in tests. Instead, modify timestamps or other values directly (e.g., read a log, bump `completed_at`, write it back).
- Prefer the `recording_console` fixture over `capsys`/`capfd` for capturing output. It captures both Rich console output and Python logging output (via `RichHandler`).
- Do not write Python code as strings inside test functions (e.g., `file.write_text("def ...")`). Instead, create real `.py` fixture files under `tests/`. The `tests/local_eval/` project is a good place for test tasks, filters, and other registered objects.
