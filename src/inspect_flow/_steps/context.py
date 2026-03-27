from contextvars import ContextVar

from inspect_ai.log import EvalLog


class StepContext:
    """Tracks dirty logs during step execution.

    Uses log.location as the key — later modifications to the same log
    overwrite earlier ones.
    """

    def __init__(self) -> None:
        self._dirty: dict[str, EvalLog] = {}

    def mark_dirty(self, logs: list[EvalLog]) -> None:
        """Register logs as modified."""
        for log in logs:
            self._dirty[log.location] = log

    @property
    def dirty(self) -> dict[str, EvalLog]:
        return dict(self._dirty)


_current_context: ContextVar[StepContext | None] = ContextVar(
    "_current_context", default=None
)


def get_step_context() -> StepContext:
    """Get the current step context.

    Raises:
        RuntimeError: If called outside of a step context.
    """
    ctx = _current_context.get()
    if ctx is None:
        raise RuntimeError(
            "No active step context. "
            "mark_dirty() and other context methods must be called "
            "within run_step() or a @step-decorated function."
        )
    return ctx


def mark_dirty(logs: list[EvalLog]) -> None:
    """Register logs as modified in the current step context.

    Args:
        logs: Modified EvalLog objects to track.

    Raises:
        RuntimeError: If called outside of a step context.
    """
    get_step_context().mark_dirty(logs)


def init_context() -> StepContext:
    ctx = StepContext()
    _current_context.set(ctx)
    return ctx


def clear_context() -> None:
    _current_context.set(None)
