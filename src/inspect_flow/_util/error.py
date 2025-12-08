import subprocess
import sys
from types import TracebackType
from typing import Callable


def exception_hook() -> Callable[..., None]:
    sys_handler = sys.excepthook

    def handler(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType,
    ) -> None:
        if getattr(exception, "_flow_handled", False) or isinstance(
            exception, subprocess.CalledProcessError
        ):
            # Exception already handled, do not print again
            sys.exit(getattr(exception, "returncode", 1))
        else:
            sys_handler(exception_type, exception, traceback)

    return handler


_exception_hook_set: bool = False


def set_exception_hook() -> None:
    global _exception_hook_set
    if not _exception_hook_set:
        sys.excepthook = exception_hook()
        _exception_hook_set = True
