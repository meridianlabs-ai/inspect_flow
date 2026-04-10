from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator, Sequence

from inspect_ai.log import EvalLog, read_eval_log, write_eval_log

from inspect_flow._store.store import FlowStore
from inspect_flow._util.console import console, path


@dataclass
class StepContext:
    logs: list[EvalLog] = field(default_factory=list)
    dirty: dict[str, EvalLog] = field(default_factory=dict)
    depth: int = 0
    dry_run: bool = False
    total: int | None = None
    store: FlowStore | None = None

    def write_dirty(self) -> None:
        """Write all dirty logs to disk and add new paths to the store."""
        if not self.dry_run:
            for log in self.dirty.values():
                with console.status("[dim]Writing[/dim]"):
                    write_eval_log(
                        log, log.location, if_match_etag=log.etag, header_only=True
                    )
            if self.store:
                self.store.import_log_path(
                    [log.location for log in self.dirty.values()]
                )
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
    prefix = "[DRY RUN] " if context.dry_run else ""
    console.print(prefix, path(location), sep="")


@contextmanager
def step_context(
    logs_or_paths: Sequence[EvalLog | str],
    *,
    dry_run: bool = False,
    step_name: str = "step",
    total: int | None = None,
    store: FlowStore | None = None,
) -> Iterator[StepContext]:
    """Get or create a step context, optionally resolving a log.

    When outer and given a path, reads the full log from disk.
    When nested and given a path, raises ValueError.
    When given an EvalLog, passes it through.
    When given None, sets context.log to None.

    On clean exit, the outer context writes all dirty logs.
    """
    existing = _step_context_var.get()
    is_outer = existing is None

    if is_outer:
        context = StepContext(dry_run=dry_run, total=total, store=store)
        token = _step_context_var.set(context)
    else:
        context = existing
        token = None

    logs = []
    for log_or_path in logs_or_paths:
        if isinstance(log_or_path, EvalLog):
            logs.append(log_or_path)
            _log_header(log_or_path.location, context)
        else:
            _log_header(log_or_path, context)
            try:
                with console.status("[dim]Reading[/dim]"):
                    logs.append(read_log(log_or_path, header_only=True))
            except Exception:
                console.print("  [red]Could not read log[/red]")
    context.logs = logs

    try:
        yield context
        if is_outer:
            context.write_dirty()
    finally:
        if token:
            _step_context_var.reset(token)
