from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator, cast

from inspect_ai.log import EvalLog, read_eval_log, write_eval_log
from inspect_ai.log._file import read_eval_log_headers

from inspect_flow._display.path_progress import ReadLogsProgress
from inspect_flow._store.store import FlowStore
from inspect_flow._util.console import console


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


def read_log_headers(paths: list[str]) -> list[EvalLog]:
    """Batch-read log headers from a list of paths."""
    with ReadLogsProgress() as progress:
        return read_eval_log_headers(paths, progress=progress)


@contextmanager
def step_context(
    logs_or_paths: list[str] | list[EvalLog],
    *,
    dry_run: bool = False,
    total: int | None = None,
    store: FlowStore | None = None,
) -> Iterator[StepContext]:
    """Get or create a step context, optionally resolving a log.

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

    if logs_or_paths and isinstance(logs_or_paths[0], str):
        context.logs = read_log_headers(cast(list[str], logs_or_paths))
    else:
        context.logs = list(cast(list[EvalLog], logs_or_paths))

    try:
        yield context
        if is_outer:
            context.write_dirty()
    finally:
        if token:
            _step_context_var.reset(token)
