import logging
import subprocess
import sys
from types import TracebackType
from typing import Callable

import click
from botocore.exceptions import TokenRetrievalError
from rich.traceback import install

from inspect_flow._util.console import flow_print

_sso_error_shown: bool = False


def print_sso_error() -> None:
    """Print a friendly message for expired AWS SSO tokens (once per process)."""
    global _sso_error_shown
    if _sso_error_shown:
        return
    _sso_error_shown = True
    flow_print(
        "[bold red]AWS SSO token has expired or is not available.[/bold red]"
        " Run `aws sso login` to authenticate, then retry."
    )


def exception_hook() -> Callable[..., None]:
    sys_handler = sys.excepthook

    def handler(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType,
    ) -> None:
        if isinstance(exception, (FlowHandledError, subprocess.CalledProcessError)):
            # Exception already handled, do not print again
            sys.exit(getattr(exception, "returncode", 1))
        elif isinstance(exception, KeyboardInterrupt):
            # Exit cleanly without traceback (130 = 128 + SIGINT)
            sys.exit(130)
        elif isinstance(exception, click.Abort):
            # Exit cleanly without traceback
            sys.exit(1)
        elif isinstance(exception, TokenRetrievalError):
            print_sso_error()
            sys.exit(1)
        else:
            sys_handler(exception_type, exception, traceback)

    return handler


_exception_hook_set: bool = False


class _SSOTokenRefreshFilter(logging.Filter):
    """Suppress boto/aiobotocore WARNING logs about SSO token refresh failures."""

    _KEYWORDS = (
        "SSO token refresh attempt failed",
        "Refreshing temporary credentials failed during mandatory refresh period",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if any(kw in msg for kw in self._KEYWORDS):
            print_sso_error()
            return False
        return True


def set_exception_hook(force: bool = False) -> None:
    global _exception_hook_set
    if not _exception_hook_set or force:
        install(show_locals=False, suppress=[click])
        sys.excepthook = exception_hook()
        sso_filter = _SSOTokenRefreshFilter()
        for name in (
            "aiobotocore.tokens",
            "aiobotocore.credentials",
            "botocore.tokens",
            "botocore.credentials",
        ):
            logging.getLogger(name).addFilter(sso_filter)
        _exception_hook_set = True


class FlowHandledError(Exception):
    """Wrapper for exceptions that have already been printed to the console."""

    pass


class NoLogsError(Exception):
    """Raised when no logs are found in the specified log directory."""

    pass
