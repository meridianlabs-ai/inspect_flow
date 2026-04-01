from collections.abc import Iterator
from typing import ParamSpec, Sequence

from inspect_ai.log import EvalLog, list_eval_logs, read_eval_log

from inspect_flow._steps.step import StepFunction


def _read_log(log_or_path: EvalLog | str, header_only: bool) -> Iterator[EvalLog]:
    if isinstance(log_or_path, EvalLog):
        yield log_or_path
    else:
        log_paths = list_eval_logs(log_or_path, recursive=True)
        for p in log_paths:
            yield read_eval_log(p.name, header_only=header_only)


def _read_logs(
    logs_or_paths: Sequence[EvalLog | str], header_only: bool
) -> Iterator[EvalLog]:
    for item in logs_or_paths:
        yield from _read_log(item, header_only=header_only)


P = ParamSpec("P")


def run_step(
    step: StepFunction[P],
    logs: Sequence[EvalLog | str] | EvalLog | str,
    *args: P.args,
    **kwargs: P.kwargs,
) -> None:
    """Run a step function on the given logs.

    Args:
        step: The step function to run.
        logs: EvalLog objects or paths to eval logs to process.
        args: Positional arguments to pass to the step function.
        kwargs: Keyword arguments to pass to the step function.
    """
    if isinstance(logs, (EvalLog, str)):
        logs = [logs]
    for log in _read_logs(logs, header_only=False):
        step(log, *args, **kwargs)
