from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import partial
from typing import Iterator, cast

from inspect_ai._util._async import run_coroutine, tg_collect
from inspect_ai.log import EvalLog, write_eval_log
from inspect_ai.log._file import read_eval_log_async

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


def read_log_headers(paths: list[str]) -> list[EvalLog]:
    """Batch-read log headers, skipping paths that cannot be read."""

    async def _read_log_headers() -> list[EvalLog]:
        async def _read(path: str) -> EvalLog | None:
            try:
                log = await read_eval_log_async(path, header_only=True)
            except Exception:
                console.print(f"[red]Could not read log {path}[/red]")
                return None
            progress.after_read_log(path)
            return log

        return [
            log
            for log in await tg_collect([partial(_read, p) for p in paths])
            if log is not None
        ]

    with ReadLogsProgress() as progress:
        progress.before_reading_logs(len(paths))
        return run_coroutine(_read_log_headers())


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
