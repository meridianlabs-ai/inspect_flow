from pathlib import Path

PKG_NAME = Path(__file__).parent.parent.stem

DEFAULT_LOG_LEVEL = "warning"

# Exit code signalling that a command ran successfully but the result is
# incomplete (e.g. some tasks errored, or `check` found missing logs). Distinct
# from exit code 1, which is used for handled errors/exceptions.
EXIT_INCOMPLETE = 2
