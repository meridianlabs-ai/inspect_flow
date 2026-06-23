from pathlib import Path

PKG_NAME = Path(__file__).parent.parent.stem

DEFAULT_LOG_LEVEL = "warning"

# Exit code signalling that a command ran successfully but the result is
# incomplete (e.g. some tasks errored, or `check` found missing logs). Distinct
# from exit code 1 (handled errors/exceptions) and exit code 2 (click's
# conventional usage-error code), so scripts can tell an incomplete run apart
# from a malformed invocation.
EXIT_INCOMPLETE = 3
