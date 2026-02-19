# Tests

- Never use `time.sleep()` in tests. Instead, modify timestamps or other values directly (e.g., read a log, bump `completed_at`, write it back).
