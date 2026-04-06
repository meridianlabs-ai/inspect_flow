from collections.abc import Callable
from typing import Any, Concatenate, NamedTuple, ParamSpec, Protocol, cast, overload

from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_name,
)
from inspect_ai.log import EvalLog

from inspect_flow._steps.context import step_context
from inspect_flow._store.store import FlowStore
from inspect_flow._util.console import console

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
            dry_run = bool(kwargs.pop("dry_run", False))
            store = cast(FlowStore | None, kwargs.pop("store", None))
            with step_context(
                log_or_path, dry_run=dry_run, step_name=f.__name__, store=store
            ) as context:
                if context.log is None:
                    return None

                indent = "  " * (context.depth + 1)
                console.print(
                    f"{indent}[dim]{_format_step_call(f.__name__, kwargs)}[/dim]"
                )
                context.depth += 1

                saved_samples = context.log.samples
                saved_reductions = context.log.reductions
                log_in = (
                    context.log.model_copy(update={"samples": None, "reductions": None})
                    if header_only
                    else context.log
                )

                step_result = _to_step_result(f(log_in, *args, **kwargs))
                context.depth -= 1

                if step_result.log and header_only:
                    step_result = step_result._replace(
                        log=step_result.log.model_copy(
                            update={
                                "samples": saved_samples,
                                "reductions": saved_reductions,
                            }
                        )
                    )

                if step_result.log and step_result.modified:
                    context.dirty[step_result.log.location] = step_result.log
                    context.log = step_result.log

                if step_result.flush:
                    context.write_dirty()

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
