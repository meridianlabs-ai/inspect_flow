from collections.abc import Callable
from typing import Any

from inspect_ai.log import EvalLog, list_eval_logs, read_eval_log, write_eval_log

from inspect_flow._steps.context import clear_context, init_context


def run_step(
    step: Callable[..., list[EvalLog]],
    paths: list[str],
    *,
    recursive: bool = True,
    **kwargs: Any,
) -> list[EvalLog]:
    """Run a step function on eval logs at the given paths.

    Reads log headers from the paths, calls the step function, and writes
    back only the logs marked dirty during execution.

    Args:
        step: A @step-decorated function.
        paths: Log files or directories.
        recursive: Recurse into directories.
        **kwargs: Additional keyword arguments passed to the step function.

    Returns:
        The modified EvalLog objects.
    """
    log_paths = [
        info.name for p in paths for info in list_eval_logs(p, recursive=recursive)
    ]
    logs = [read_eval_log(p, header_only=True) for p in log_paths]
    ctx = init_context()
    try:
        result = step(logs, **kwargs)
        for log in ctx.dirty.values():
            write_eval_log(log, log.location)
    finally:
        clear_context()
    return result
