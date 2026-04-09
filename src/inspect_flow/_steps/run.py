from collections.abc import Sequence
from typing import ParamSpec

from inspect_ai.log import EvalLog, list_eval_logs
from inspect_ai.log._file import read_eval_log_headers

from inspect_flow._steps.context import step_context
from inspect_flow._steps.step import WrappedStepFunction
from inspect_flow._store.store import FlowStore
from inspect_flow._types.flow_types import LogFilter
from inspect_flow._types.log_filter import resolve_log_filters
from inspect_flow._util.console import console, flow_print


def _expand_paths(
    logs_or_paths: Sequence[EvalLog | str], recursive: bool = True
) -> list[EvalLog | str]:
    """Expand directories to individual log paths, pass EvalLog objects through."""
    result: list[EvalLog | str] = []
    for item in logs_or_paths:
        if isinstance(item, EvalLog):
            result.append(item)
        else:
            for info in list_eval_logs(item, recursive=recursive):
                result.append(info.name)
    return result


P = ParamSpec("P")


def run_step(
    step: WrappedStepFunction[P],
    logs: Sequence[EvalLog | str] | EvalLog | str,
    dry_run: bool = False,
    filter: LogFilter | str | Sequence[LogFilter | str] | None = None,
    exclude: LogFilter | str | Sequence[LogFilter | str] | None = None,
    recursive: bool = True,
    expand_paths: bool = True,
    store: FlowStore | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> None:
    """Run a step function on the given logs.

    Args:
        step: The step function to run.
        logs: EvalLog objects or paths to eval logs to process.
        filter: A log filter or sequence of filters. Only logs that pass
            all filters are processed. Accepts callables, registered names,
            or "file.py@name" strings.
        exclude: A log filter or sequence of filters. Logs that pass any
            exclude filter are skipped. Accepts the same formats as filter.
        dry_run: If True, run steps but skip writing logs to disk.
        recursive: Recurse into directories (default: True).
        expand_paths: Expand directory paths to individual log paths
            (default: True). Set to False when paths are already resolved.
        store: Optional flow store. Written logs are added to the store.
        args: Positional arguments to pass to the step function.
        kwargs: Keyword arguments to pass to the step function.
    """
    if dry_run:
        flow_print("[DRY RUN] will not write changes")

    if isinstance(logs, (EvalLog, str)):
        logs = [logs]
    log_paths = _expand_paths(logs, recursive=recursive) if expand_paths else list(logs)
    include_filters = resolve_log_filters(filter)
    exclude_filters = resolve_log_filters(exclude)
    if include_filters or exclude_filters:
        with console.status("[dim]Filtering...[/dim]"):
            paths = [log for log in log_paths if isinstance(log, str)]
            eval_logs = [log for log in log_paths if isinstance(log, EvalLog)]
            log_headers = read_eval_log_headers(paths) + eval_logs
            for nf in include_filters:
                before = len(log_headers)
                log_headers = [log for log in log_headers if nf.fn(log)]
                flow_print(
                    f"Filter: {nf.name} — {len(log_headers)}/{before} logs matched"
                )
            for nf in exclude_filters:
                before = len(log_headers)
                log_headers = [log for log in log_headers if not nf.fn(log)]
                flow_print(
                    f"Exclude: {nf.name} — {len(log_headers)}/{before} logs remaining"
                )
            eval_log_map = {log.location: log for log in eval_logs}
            log_paths = [
                eval_log_map.get(log.location, log.location) for log in log_headers
            ]
    if not log_paths:
        flow_print("No logs found", format="warning")
        return
    log_paths = sorted(log_paths, key=lambda p: p if isinstance(p, str) else p.location)
    total = len(log_paths)
    for i, log_or_path in enumerate(log_paths, 1):
        with step_context(
            log_or_path, dry_run=dry_run, index=i, total=total, store=store
        ) as ctx:
            if ctx.log is None:
                continue
            step(log_or_path, *args, **kwargs)
