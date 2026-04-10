from typing import (
    Any,
    Callable,
    Concatenate,
    NamedTuple,
    ParamSpec,
    Protocol,
    cast,
    overload,
)

from inspect_ai._util.registry import (
    RegistryInfo,
    registry_add,
    registry_name,
)
from inspect_ai.log import EvalLog

from inspect_flow._steps.context import step_context
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._util.console import console

STEP_TYPE = "step"


class StepResult(NamedTuple):
    """Fine-grained return type for @step functions.

    Steps can also return a sequence of EvalLog directly (equivalent to
    StepResult(logs=logs, modified=True)) or [] (equivalent to
    StepResult(modified=False, skip_log_steps=True)).
    """

    logs: list[EvalLog]
    """The logs returned to the caller."""

    modified: bool = True
    """Whether the logs were modified. When True, the logs are written back to disk
    and becomes the current log for subsequent nested steps. When False, the log
    is returned but the current context log is not advanced."""

    flush: bool = False
    """Write all dirty logs immediately, even if nested inside an outer step."""

    skip_log_steps: bool = False
    """Skip remaining steps for this log. run_step will move to the next log."""


P = ParamSpec("P")
StepFunction = Callable[Concatenate[list[EvalLog], P], StepResult | list[EvalLog]]
WrappedStepFunction = Callable[Concatenate[list[EvalLog] | list[str], P], list[EvalLog]]


class _StepDecorator(Protocol):
    @overload
    def __call__(
        self, func: Callable[Concatenate[EvalLog, P], EvalLog]
    ) -> Callable[Concatenate[EvalLog | str, P], EvalLog]: ...

    @overload
    def __call__(self, func: StepFunction[P]) -> WrappedStepFunction[P]: ...


def _format_step_call(name: str, n_logs: int, kwargs: dict[str, Any]) -> str:
    def _format_value(v: Any) -> str:
        if isinstance(v, tuple):
            return repr(list(v))
        return repr(v)

    def _is_empty(v: Any) -> bool:
        return v is None or (isinstance(v, (list, tuple)) and len(v) == 0)

    args_str = ", ".join(
        f"{k}={_format_value(v)}" for k, v in kwargs.items() if not _is_empty(v)
    )
    return (
        f"{name}(logs={n_logs}, {args_str})" if args_str else f"{name}(logs={n_logs})"
    )


def _to_step_result(result: StepResult | list[EvalLog]) -> StepResult:
    if isinstance(result, StepResult):
        return result
    else:
        return StepResult(logs=result, modified=True, skip_log_steps=False)


def step(
    func: StepFunction[P],
) -> WrappedStepFunction[P]:
    """Decorator to register a step function.

    Args:
        func: A function that takes a list of EvalLog objects and performs
            operations on them (tag, validate, copy, etc.).
    """

    def decorator(f: StepFunction[P]) -> WrappedStepFunction[P]:
        def step_wrapper(
            logs_or_paths: list[str] | list[EvalLog],
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> list[EvalLog]:
            dry_run = bool(kwargs.pop("dry_run", False))
            store_value = kwargs.pop("store", None)
            if isinstance(store_value, str):
                store = store_factory(
                    store_value, base_dir=".", create=True, quiet=True
                )
            else:
                store = cast(FlowStore | None, store_value)
            with step_context(logs_or_paths, dry_run=dry_run, store=store) as context:
                if not context.logs:
                    return []

                indent = "  " * (context.depth + 1)
                console.print(
                    f"{indent}{_format_step_call(f.__name__, len(context.logs), kwargs)}"
                )
                context.depth += 1

                step_result = _to_step_result(f(context.logs, *args, **kwargs))
                context.depth -= 1

                if step_result.logs and step_result.modified:
                    for log in step_result.logs:
                        context.dirty[log.location] = log
                    context.logs = step_result.logs

                if step_result.flush:
                    context.write_dirty()

                if step_result.skip_log_steps:
                    return []
                else:
                    return step_result.logs

        step_wrapper._step_func = f  # type: ignore[attr-defined]
        name = registry_name(f, f.__name__)
        registry_add(
            step_wrapper,
            RegistryInfo.model_construct(type=STEP_TYPE, name=name),
        )
        return step_wrapper

    return decorator(func)
