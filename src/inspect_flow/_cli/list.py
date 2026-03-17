import io
import os
import re
import subprocess
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime
from functools import partial

import click
from inspect_ai._util._async import run_coroutine, tg_collect
from inspect_ai.log import EvalLog, list_eval_logs, read_eval_log_async
from rich.console import Console
from rich.progress import Progress
from rich.text import Text
from rich.tree import Tree
from typing_extensions import Unpack

from inspect_flow._cli.store import StoreOptionArgs, init_store, store_options
from inspect_flow._runner.task_log import TaskInfo, unique_task_names
from inspect_flow._util.console import flow_print, path

_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T")


# -- Sorting and grouping ----------------------------------------------------


def _sort_logs(logs: Collection[str]) -> list[str]:
    with_ts: list[str] = []
    without_ts: list[str] = []
    for log in logs:
        basename = log.rsplit("/", 1)[-1]
        if _TIMESTAMP_RE.match(basename):
            with_ts.append(log)
        else:
            without_ts.append(log)
    with_ts.sort(key=lambda p: p.rsplit("/", 1)[-1], reverse=True)
    without_ts.sort(key=lambda p: p.rsplit("/", 1)[-1])
    return with_ts + without_ts


def _group_by_dir(log_paths: Collection[str]) -> list[list[str]]:
    """Group logs by directory, sorted by most recent file descending."""
    groups: dict[str, list[str]] = {}
    for log_path in log_paths:
        dir_path = log_path.rsplit("/", 1)[0] if "/" in log_path else ""
        groups.setdefault(dir_path, []).append(log_path)

    sorted_groups = [_sort_logs(paths) for paths in groups.values()]

    ts_groups: list[list[str]] = []
    non_ts_groups: list[list[str]] = []
    for group in sorted_groups:
        if _TIMESTAMP_RE.match(group[0].rsplit("/", 1)[-1]):
            ts_groups.append(group)
        else:
            non_ts_groups.append(group)

    ts_groups.sort(key=lambda g: g[0].rsplit("/", 1)[-1], reverse=True)
    non_ts_groups.sort(key=lambda g: g[0].rsplit("/", 1)[-1])
    return ts_groups + non_ts_groups


# -- Header reading and qualifier computation ---------------------------------


async def _read_header(
    log_path: str, on_read: Callable[[], None] | None = None
) -> tuple[str, EvalLog | None]:
    try:
        result = log_path, await read_eval_log_async(log_path, header_only=True)
    except Exception:
        result = log_path, None
    if on_read:
        on_read()
    return result


def _read_headers(
    log_paths: list[str], progress: Progress | None = None
) -> dict[str, EvalLog]:
    on_read: Callable[[], None] | None = None
    if progress is not None:
        for task in progress.tasks:
            progress.remove_task(task.id)
        task_id = progress.add_task("Reading logs…", total=len(log_paths))
        on_read = partial(progress.advance, task_id)
    results = run_coroutine(
        tg_collect([partial(_read_header, p, on_read) for p in log_paths])
    )
    return {p: h for p, h in results if h is not None}


def _eval_log_to_task_info(header: EvalLog) -> TaskInfo:
    model_roles = (
        {k: v.model for k, v in header.eval.model_roles.items()}
        if header.eval.model_roles
        else None
    )
    return TaskInfo(
        name=header.eval.task,
        model=header.eval.model,
        args=header.eval.task_args_passed or None,
        model_roles=model_roles,
        solver=header.eval.solver,
        version=header.eval.task_version,
        config=header.eval.model_generate_config,
    )


_STATUS_STYLES: dict[str, str] = {
    "success": "green",
    "cancelled": "yellow",
    "error": "red",
    "started": "cyan",
}


def _duration_str(header: EvalLog) -> str:
    started = header.stats.started_at
    completed = header.stats.completed_at
    if not started or not completed:
        return ""
    delta = datetime.fromisoformat(completed) - datetime.fromisoformat(started)
    return str(delta).split(".")[0]


def _samples_str(header: EvalLog) -> str:
    if header.results:
        return f"{header.results.completed_samples}/{header.results.total_samples}"
    total = (header.eval.dataset.samples or 0) * (header.eval.config.epochs or 1)
    return f"0/{total}" if total else ""


@dataclass
class LogEntry:
    log_path: str
    task: str
    qualifier: Text
    status: str
    samples: str
    duration: str


def _compute_entries(
    log_paths: list[str], headers: dict[str, EvalLog]
) -> list[LogEntry]:
    """Compute task name and qualifier for a set of logs in the same directory."""
    valid = [p for p in log_paths if p in headers]
    task_infos = [_eval_log_to_task_info(headers[p]) for p in valid]
    qualifiers = unique_task_names(task_infos)

    entries = [
        LogEntry(
            p,
            name,
            qual,
            headers[p].status,
            _samples_str(headers[p]),
            _duration_str(headers[p]),
        )
        for p, (name, qual) in zip(valid, qualifiers.names, strict=True)
    ]
    valid_set = set(valid)
    for p in log_paths:
        if p not in valid_set:
            entries.append(LogEntry(p, "", Text(), "", "", ""))
    return entries


# -- Formatting ---------------------------------------------------------------


_RIGHT_ALIGN = frozenset({3, 4})  # samples, duration
_COL_PAD = 2
_TREE_GUIDE_WIDTH = 4


def _make_cells(entry: LogEntry, filename_only: bool = False) -> list[Text]:
    log_path = entry.log_path.rsplit("/", 1)[-1] if filename_only else entry.log_path
    return [
        Text(entry.task),
        entry.qualifier,
        Text(entry.status, style=_STATUS_STYLES.get(entry.status, "")),
        Text(entry.samples),
        Text(entry.duration),
        path(log_path),
    ]


def _col_widths(rows: list[list[Text]]) -> list[int]:
    return [max(row[i].cell_len for row in rows) for i in range(len(rows[0]))]


def _break_columns(widths: list[int], available: int) -> list[list[int]]:
    visible = [i for i in range(len(widths)) if widths[i] > 0]
    breaks: list[list[int]] = []
    line: list[int] = []
    line_w = 0
    for i in visible:
        w = widths[i] + (_COL_PAD if line else 0)
        if line and line_w + w > available:
            breaks.append(line)
            line = [i]
            line_w = widths[i]
        else:
            line.append(i)
            line_w += w
    if line:
        breaks.append(line)
    return breaks


def _format_row(cells: list[Text], widths: list[int], breaks: list[list[int]]) -> Text:
    result = Text()
    for bi, cols in enumerate(breaks):
        if bi > 0:
            result.append("\n  ")
        for j, ci in enumerate(cols):
            if j > 0:
                result.append(" " * _COL_PAD)
            cell = cells[ci]
            pad = widths[ci] - cell.cell_len
            if ci in _RIGHT_ALIGN:
                if pad > 0:
                    result.append(" " * pad)
                result.append_text(cell)
            else:
                result.append_text(cell)
                if j < len(cols) - 1 and pad > 0:
                    result.append(" " * pad)
    return result


def _render_entries(entries: list[LogEntry]) -> str:
    if not entries:
        return ""
    rows = [_make_cells(e) for e in entries]
    widths = _col_widths(rows)
    breaks = _break_columns(widths, Console().size.width)
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=2**15)
    for cells in rows:
        console.print(_format_row(cells, widths, breaks))
    return buf.getvalue()


def _render_tree(renderable: Tree) -> str:
    buf = io.StringIO()
    Console(file=buf, force_terminal=True, width=2**15).print(renderable)
    return buf.getvalue()


def _common_prefix(dirs: list[str]) -> str:
    if len(dirs) <= 1:
        return dirs[0] if dirs else ""
    split = [d.split("/") for d in dirs]
    prefix: list[str] = []
    for parts in zip(*split, strict=False):
        if len(set(parts)) == 1:
            prefix.append(parts[0])
        else:
            break
    return "/".join(prefix)


def _format_tree(dir_entries: list[tuple[str, list[LogEntry]]]) -> str:
    all_cells = [
        _make_cells(e, filename_only=True)
        for _, entries in dir_entries
        for e in entries
    ]
    widths = _col_widths(all_cells) if all_cells else []

    dirs = [d for d, _ in dir_entries]
    prefix = _common_prefix(dirs)
    max_depth = max(
        (
            len(
                [
                    p
                    for p in (d[len(prefix) :].lstrip("/") if prefix else d).split("/")
                    if p
                ]
            )
            for d in dirs
        ),
        default=0,
    )
    tree_indent = _TREE_GUIDE_WIDTH * (max_depth + 1)
    breaks = _break_columns(widths, Console().size.width - tree_indent)

    tree = Tree(prefix or ".")
    nodes: dict[str, Tree] = {}
    idx = 0
    for dir_path, entries in dir_entries:
        rel = dir_path[len(prefix) :].lstrip("/") if prefix else dir_path
        parts = [p for p in rel.split("/") if p]
        current: Tree = tree
        built = ""
        for part in parts:
            built = f"{built}/{part}" if built else part
            if built not in nodes:
                nodes[built] = current.add(part)
            current = nodes[built]
        for _ in entries:
            current.add(_format_row(all_cells[idx], widths, breaks))
            idx += 1

    return _render_tree(tree)


def _page_string(content: str) -> None:
    env = os.environ.copy()
    env["LESS"] = env.get("LESS", "") + " -RX"
    pager = env.get("PAGER", "less")
    proc = subprocess.Popen(pager.split(), stdin=subprocess.PIPE, env=env)
    assert proc.stdin
    try:
        proc.stdin.write(content.encode())
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
        proc.wait()


def _echo_tree(dir_groups: list[list[str]], progress: Progress | None = None) -> None:
    all_paths = [p for group in dir_groups for p in group]
    headers = _read_headers(all_paths, progress=progress)
    if progress:
        progress.stop()

    dir_entries: list[tuple[str, list[LogEntry]]] = []
    for group in dir_groups:
        entries = _compute_entries(group, headers)
        dir_path = group[0].rsplit("/", 1)[0] if "/" in group[0] else ""
        dir_entries.append((dir_path, entries))

    output = _format_tree(dir_entries)
    page_size = Console().size.height - 1
    if output.count("\n") <= page_size:
        click.echo(output, nl=False)
    else:
        _page_string(output)


# -- Paging -------------------------------------------------------------------


def _process_groups(
    dir_groups: list[list[str]], progress: Progress | None = None
) -> list[LogEntry]:
    all_paths = [p for group in dir_groups for p in group]
    headers = _read_headers(all_paths, progress=progress)
    entries: list[LogEntry] = []
    for group in dir_groups:
        entries.extend(_compute_entries(group, headers))
    return entries


def _echo_logs(
    log_paths: Collection[str],
    progress: Progress | None = None,
    output_format: str = "table",
) -> None:
    dir_groups = _group_by_dir(log_paths)
    if output_format == "tree":
        _echo_tree(dir_groups, progress)
        return
    total = sum(len(g) for g in dir_groups)
    page_size = Console().size.height - 1
    if total <= page_size:
        entries = _process_groups(dir_groups, progress=progress)
        if progress:
            progress.stop()
        click.echo(_render_entries(entries), nl=False)
    else:
        _paged_output(dir_groups, page_size, progress=progress)


def _paged_output(
    dir_groups: list[list[str]],
    page_size: int,
    progress: Progress | None = None,
) -> None:
    env = os.environ.copy()
    env["LESS"] = env.get("LESS", "") + " -RX"
    pager = env.get("PAGER", "less")
    proc = subprocess.Popen(pager.split(), stdin=subprocess.PIPE, env=env)
    assert proc.stdin
    try:
        pending: list[list[str]] = []
        pending_count = 0
        first = True
        for group in dir_groups:
            pending.append(group)
            pending_count += len(group)
            if pending_count >= page_size:
                entries = _process_groups(pending, progress=progress if first else None)
                if first and progress:
                    progress.stop()
                    progress = None
                first = False
                proc.stdin.write(_render_entries(entries).encode())
                proc.stdin.flush()
                pending = []
                pending_count = 0
        if pending:
            entries = _process_groups(pending, progress=progress if first else None)
            if first and progress:
                progress.stop()
            proc.stdin.write(_render_entries(entries).encode())
            proc.stdin.flush()
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
        proc.wait()


# -- CLI commands -------------------------------------------------------------


@click.group("list")
def list_command() -> None:
    """CLI command to list flow entities."""
    pass


@list_command.command("log", help="List logs")
@store_options
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "tree"]),
    default="table",
    help="Output format",
)
@click.argument("path", required=False, default=None)
def list_log(
    path: str | None, output_format: str, **kwargs: Unpack[StoreOptionArgs]
) -> None:
    progress = Progress(transient=True)
    progress.add_task("Listing logs…", total=None)
    progress.start()
    if path is not None:
        log_infos = list_eval_logs(log_dir=path, recursive=True)
        if not log_infos:
            progress.stop()
            flow_print("No logs found in", path)
            return
        _echo_logs(
            [info.name for info in log_infos],
            progress=progress,
            output_format=output_format,
        )
    else:
        flow_store = init_store(quiet=True, **kwargs)
        if not flow_store:
            progress.stop()
            return
        log_files = flow_store.get_logs()
        if not log_files:
            progress.stop()
            flow_print("No logs in store")
            return
        _echo_logs(log_files, progress=progress, output_format=output_format)
