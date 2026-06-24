"""Helpers for detecting whether the process is attached to a terminal."""

import os
import sys


def stdin_is_interactive() -> bool:
    """`True` if stdin is an interactive terminal we can prompt on."""
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (ValueError, OSError):
        return False


def stdout_is_terminal() -> bool:
    """`True` if stdout is a terminal (e.g. safe to page output)."""
    try:
        return os.isatty(1)
    except OSError:
        return False
