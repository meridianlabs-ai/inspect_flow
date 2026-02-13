import subprocess
import sys
from types import TracebackType
from typing import Callable

import click
from botocore.exceptions import TokenRetrievalError
from rich.traceback import install

from inspect_flow._util.console import flow_print


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
        # elif isinstance(exception, KeyboardInterrupt):
        #     # Exit cleanly without traceback (130 = 128 + SIGINT)
        #     sys.exit(130)
        # elif isinstance(exception, click.Abort):
        #     # Exit cleanly without traceback
        #     sys.exit(1)
        elif isinstance(exception, TokenRetrievalError):
            # No need for stack trace - just print the error message
            flow_print(
                f"[bold red]{exception.__class__.__name__}:[/bold red] {str(exception)}"
            )
            sys.exit(1)
        else:
            sys_handler(exception_type, exception, traceback)

    return handler


_exception_hook_set: bool = False


def set_exception_hook(force: bool = False) -> None:
    global _exception_hook_set
    if not _exception_hook_set or force:
        install(show_locals=False, suppress=[click])
        sys.excepthook = exception_hook()
        _exception_hook_set = True


class FlowHandledError(Exception):
    """Wrapper for exceptions that have already been printed to the console."""

    pass


class NoLogsError(Exception):
    """Raised when no logs are found in the specified log directory."""

    pass
