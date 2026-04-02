from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Concatenate, NamedTuple, ParamSpec, Protocol, overload

from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_name,
)
from inspect_ai.log import EvalLog, read_eval_log, write_eval_log

from inspect_flow._util.console import console, path

STEP_TYPE = "step"


class StepResult(NamedTuple):
    """Fine-grained return type for @step functions.

    Steps can also return an EvalLog directly (equivalent to
    StepResult(log=log, modified=True)) or None (equivalent to
    StepResult(modified=False, skip_log_steps=True)).
    """

    log: EvalLog | None = None
    """The log to pass to subsequent steps. None to skip remaining steps for this log."""

    modified: bool = True
    """Whether the log was modified. Controls whether the log is written back."""

    flush: bool = False
    """Write all dirty logs immediately, even if nested inside an outer step."""

    skip_log_steps: bool = False
    """Skip remaining steps for this log. run_step will move to the next log."""


P = ParamSpec("P")
StepFunction = Callable[Concatenate[EvalLog, P], StepResult | EvalLog | None]
WrappedStepFunction = Callable[Concatenate[EvalLog | str, P], EvalLog | None]


class _StepDecorator(Protocol):
    @overload
    def __call__(
        self, func: Callable[Concatenate[EvalLog, P], EvalLog]
    ) -> Callable[Concatenate[EvalLog | str, P], EvalLog]: ...

    @overload
    def __call__(self, func: StepFunction[P]) -> WrappedStepFunction[P]: ...


@dataclass
class StepContext:
    dirty: dict[str, EvalLog] = field(default_factory=dict)
    depth: int = 0


def _format_step_call(name: str, kwargs: dict[str, Any]) -> str:
    def _format_value(v: Any) -> str:
        if isinstance(v, tuple):
            return repr(list(v))
        return repr(v)

    def _is_empty(v: Any) -> bool:
        return v is None or (isinstance(v, (list, tuple)) and len(v) == 0)

    args_str = ", ".join(
        f"{k}={_format_value(v)}" for k, v in kwargs.items() if not _is_empty(v)
    )
    return f"{name}({args_str})"


# Tracks modified logs across nested step calls. None means no active step.
_step_context_var: ContextVar[StepContext | None] = ContextVar(
    "_step_context_var", default=None
)


@contextmanager
def _step_context() -> Iterator[tuple[StepContext, bool]]:
    context = _step_context_var.get()
    if context is not None:
        yield context, False
    else:
        context = StepContext()
        token = _step_context_var.set(context)
        try:
            yield context, True
        finally:
            _step_context_var.reset(token)


def _to_step_result(result: StepResult | EvalLog | None) -> StepResult:
    if isinstance(result, StepResult):
        return result
    elif isinstance(result, EvalLog):
        return StepResult(log=result, modified=True)
    else:
        return StepResult(log=None, modified=False, skip_log_steps=True)


@overload
def step(
    func: Callable[Concatenate[EvalLog, P], EvalLog],
) -> Callable[Concatenate[EvalLog | str, P], EvalLog]: ...


@overload
def step(func: StepFunction[P]) -> WrappedStepFunction[P]: ...


@overload
def step(func: None = None, *, header_only: bool = ...) -> _StepDecorator: ...


def step(
    func: StepFunction[P] | None = None,
    *,
    header_only: bool = True,
) -> WrappedStepFunction[P] | Callable[[StepFunction[P]], WrappedStepFunction[P]]:
    """Decorator to register a step function.

    Args:
        func: A function that takes a list of EvalLog objects and performs
            operations on them (tag, validate, copy, etc.).
        header_only: If False, read full logs including samples. When nested,
            raises if the outer step has not also read full logs.
    """

    def decorator(f: StepFunction[P]) -> WrappedStepFunction[P]:
        def step_wrapper(
            log_or_path: EvalLog | str | None,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> EvalLog | None:
            with _step_context() as (context, is_outer):
                if not log_or_path:
                    return None
                elif isinstance(log_or_path, EvalLog):
                    log = log_or_path
                    if context.depth == 0:
                        console.print(path(log.location))
                elif not is_outer:
                    raise ValueError(
                        f"Step '{f.__name__}' received a path but is nested inside another step. "
                        "Nested steps must be passed EvalLog objects directly, not paths."
                    )
                else:
                    # In order to write the modified log back to the same location, we need to read it fully here even if
                    # header_only=True. We could optimize this in the case where the step doesn't modify the log, but
                    # that would require reading the full log again later to support write or nested steps. In the future
                    # we could support writing just the header, so using header_only now will support that optimization
                    # later.
                    if context.depth == 0:
                        console.print(path(log_or_path))
                    with console.status("[dim]Reading[/dim]"):
                        log = read_eval_log(log_or_path, header_only=False)

                indent = "  " * (context.depth + 1)
                console.print(
                    f"{indent}[dim]{_format_step_call(f.__name__, kwargs)}[/dim]"
                )
                context.depth += 1

                log_in = (
                    log.model_copy(update={"samples": None, "reductions": None})
                    if header_only
                    else log
                )

                step_result = _to_step_result(f(log_in, *args, **kwargs))
                context.depth -= 1

                if step_result.log and header_only:
                    step_result = step_result._replace(
                        log=step_result.log.model_copy(
                            update={
                                "samples": log.samples,
                                "reductions": log.reductions,
                            }
                        )
                    )

                if step_result.log and step_result.modified:
                    context.dirty[step_result.log.location] = step_result.log

                if is_outer or step_result.flush:
                    for log in context.dirty.values():
                        with console.status("[dim]Writing[/dim]"):
                            write_eval_log(log, log.location)
                    context.dirty.clear()

                if step_result.skip_log_steps:
                    return None
                else:
                    return step_result.log

        step_wrapper._step_func = f  # type: ignore[attr-defined]
        name = registry_name(f, f.__name__)
        registry_add(
            step_wrapper,
            RegistryInfo.model_construct(type=STEP_TYPE, name=name),
        )
        return step_wrapper

    if func is not None:
        return decorator(func)
    return decorator
