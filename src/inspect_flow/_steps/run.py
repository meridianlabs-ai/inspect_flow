from typing import ParamSpec, Sequence

from inspect_ai.log import EvalLog, list_eval_logs

from inspect_flow._steps.step import WrappedStepFunction


def _expand_paths(logs_or_paths: Sequence[EvalLog | str]) -> list[EvalLog | str]:
    """Expand directories to individual log paths, pass EvalLog objects through."""
    result: list[EvalLog | str] = []
    for item in logs_or_paths:
        if isinstance(item, EvalLog):
            result.append(item)
        else:
            for info in list_eval_logs(item, recursive=True):
                result.append(info.name)
    return result


P = ParamSpec("P")


def run_step(
    step: WrappedStepFunction[P],
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
    for log in _expand_paths(logs):
        step(log, *args, **kwargs)
