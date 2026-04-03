from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from inspect_ai.log import EvalLog, read_eval_log, write_eval_log

from inspect_flow._util.console import console, path


@dataclass
class StepContext:
    log: EvalLog | None = None
    dirty: dict[str, EvalLog] = field(default_factory=dict)
    depth: int = 0
    dry_run: bool = False
    header_only: bool = True
    index: int | None = None
    total: int | None = None

    def write_dirty(self) -> None:
        """Write all dirty logs to disk and clear the set."""
        if not self.dry_run:
            for log in self.dirty.values():
                with console.status("[dim]Writing[/dim]"):
                    write_eval_log(log, log.location, header_only=self.header_only)
        self.dirty.clear()


_step_context_var: ContextVar[StepContext | None] = ContextVar(
    "_step_context_var", default=None
)


def read_log(log_or_path: EvalLog | str, header_only: bool = False) -> EvalLog:
    """Read a log from a path, or pass through an existing EvalLog."""
    if isinstance(log_or_path, EvalLog):
        return log_or_path
    return read_eval_log(log_or_path, header_only=header_only)


def _log_header(location: str, context: StepContext) -> None:
    suffix = (
        f" [dim]({context.index} of {context.total})[/dim]"
        if context.index is not None
        else ""
    )
    console.print(path(location), suffix, sep="")


@contextmanager
def step_context(
    log_or_path: EvalLog | str | None = None,
    *,
    dry_run: bool = False,
    header_only: bool = True,
    step_name: str = "step",
    index: int | None = None,
    total: int | None = None,
) -> Iterator[StepContext]:
    """Get or create a step context, optionally resolving a log.

    When outer and given a path, reads the log from disk.
    When nested and given a path, raises ValueError.
    When given an EvalLog, passes it through.
    When given None, sets context.log to None.

    On clean exit, the outer context writes all dirty logs.
    """
    existing = _step_context_var.get()
    is_outer = existing is None
    context = (
        existing
        if existing
        else StepContext(
            dry_run=dry_run, header_only=header_only, index=index, total=total
        )
    )

    if not log_or_path:
        context.log = None
    elif isinstance(log_or_path, EvalLog):
        context.log = log_or_path
        if context.depth == 0:
            _log_header(log_or_path.location, context)
    elif not is_outer:
        if context.log is None or context.log.location != log_or_path:
            raise ValueError(
                f"Step '{step_name}' received a path but is nested inside another step. "
                "Nested steps must be passed EvalLog objects directly, not paths."
            )
    else:
        if context.depth == 0:
            _log_header(log_or_path, context)
        with console.status("[dim]Reading[/dim]"):
            context.log = read_log(log_or_path, header_only=header_only)

    if is_outer:
        token = _step_context_var.set(context)
    try:
        yield context
        if is_outer:
            context.write_dirty()
    finally:
        if is_outer:
            _step_context_var.reset(token)  # type: ignore[possibly-undefined]
