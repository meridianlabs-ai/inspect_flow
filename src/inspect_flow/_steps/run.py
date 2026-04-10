from collections.abc import Sequence
from typing import ParamSpec, cast

from inspect_ai.log import EvalLog, list_eval_logs

from inspect_flow._steps.context import read_log_headers, step_context
from inspect_flow._steps.step import WrappedStepFunction
from inspect_flow._store.store import FlowStore
from inspect_flow._types.flow_types import LogFilter
from inspect_flow._types.log_filter import resolve_log_filters
from inspect_flow._util.console import console, flow_print


def _expand_paths(paths: Sequence[str], recursive: bool = True) -> list[str]:
    """Expand directories to individual log paths."""
    result: list[str] = []
    for p in paths:
        for info in list_eval_logs(p, recursive=recursive):
            result.append(info.name)
    return result


P = ParamSpec("P")


def run_step(
    step: WrappedStepFunction[P],
    logs: list[str] | list[EvalLog] | EvalLog | str,
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

    if isinstance(logs, str):
        logs = [logs]
    elif isinstance(logs, EvalLog):
        logs = [logs]

    # Resolve to homogeneous lists
    if logs and isinstance(logs[0], str):
        str_paths = cast(list[str], logs)
        resolved: list[str] | list[EvalLog] = (
            _expand_paths(str_paths, recursive=recursive) if expand_paths else str_paths
        )
    else:
        resolved = cast(list[EvalLog], logs)

    include_filters = resolve_log_filters(filter)
    exclude_filters = resolve_log_filters(exclude)
    if include_filters or exclude_filters:
        with console.status("[dim]Filtering...[/dim]"):
            if isinstance(resolved[0], str):
                log_headers = read_log_headers(cast(list[str], resolved))
                eval_log_map: dict[str, EvalLog] = {}
            else:
                log_headers = cast(list[EvalLog], resolved)
                eval_log_map = {log.location: log for log in log_headers}
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
            # Preserve original in-memory EvalLogs where possible
            resolved = [eval_log_map.get(log.location, log) for log in log_headers]

    if not resolved:
        flow_print("No logs found", format="warning")
        return

    if isinstance(resolved[0], str):
        resolved = sorted(cast(list[str], resolved))
    else:
        resolved = sorted(cast(list[EvalLog], resolved), key=lambda log: log.location)

    total = len(resolved)
    with step_context(resolved, dry_run=dry_run, total=total, store=store) as ctx:
        if ctx.logs:
            step(ctx.logs, *args, **kwargs)
