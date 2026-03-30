from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Concatenate, ParamSpec, Sequence, overload

from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_name,
)
from inspect_ai.log import EvalLog, list_eval_logs, read_eval_log, write_eval_log

STEP_TYPE = "step"

P = ParamSpec("P")
StepFunction = Callable[Concatenate[list[EvalLog], P], list[EvalLog]]
WrappedStepFunction = Callable[Concatenate[Sequence[EvalLog | str], P], list[EvalLog]]

# Tracks modified logs across nested step calls. None means no active step.
_step_dirty: ContextVar[dict[str, EvalLog] | None] = ContextVar(
    "_step_dirty", default=None
)


@contextmanager
def _step_context() -> Iterator[tuple[dict[str, EvalLog], bool]]:
    dirty = _step_dirty.get()
    if dirty is not None:
        yield dirty, False
    else:
        dirty = {}
        token = _step_dirty.set(dirty)
        try:
            yield dirty, True
        finally:
            _step_dirty.reset(token)


def _read_log(log_or_path: EvalLog | str) -> list[EvalLog]:
    if isinstance(log_or_path, EvalLog):
        return [log_or_path]
    else:
        log_paths = list_eval_logs(log_or_path, recursive=True)
        return [read_eval_log(p.name, header_only=True) for p in log_paths]


def _read_logs(logs_or_paths: Sequence[EvalLog | str]) -> list[EvalLog]:
    return [log for item in logs_or_paths for log in _read_log(item)]


@overload
def step(func: StepFunction[P]) -> WrappedStepFunction[P]: ...


@overload
def step(
    func: None = None, *, flush: bool = ...
) -> Callable[[StepFunction[P]], WrappedStepFunction[P]]: ...


def step(
    func: StepFunction[P] | None = None, *, flush: bool = False
) -> WrappedStepFunction[P] | Callable[[StepFunction[P]], WrappedStepFunction[P]]:
    """Decorator to register a step function.

    Args:
        func: A function that takes a list of EvalLog objects and performs
            operations on them (tag, validate, copy, etc.).
        flush: If True, write all dirty logs after this step even if nested,
            then clear them from the dirty tracking.
    """

    def decorator(f: StepFunction[P]) -> WrappedStepFunction[P]:
        def step_wrapper(
            logs_or_paths: Sequence[EvalLog | str], *args: P.args, **kwargs: P.kwargs
        ) -> list[EvalLog]:
            logs = _read_logs(logs_or_paths)
            with _step_context() as (dirty, is_outer):
                modified_logs = f(logs, *args, **kwargs)
                for log in modified_logs:
                    dirty[log.location] = log
                if is_outer or flush:
                    for log in dirty.values():
                        write_eval_log(log, log.location)
                    dirty.clear()
                return modified_logs

        name = registry_name(f, f.__name__)
        registry_add(
            step_wrapper,
            RegistryInfo.model_construct(type=STEP_TYPE, name=name),
        )
        return step_wrapper

    if func is not None:
        return decorator(func)
    return decorator
