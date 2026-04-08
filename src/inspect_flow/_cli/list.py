import fnmatch
import io
import os
import subprocess
import time
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from logging import getLogger

import click
import yaml
from inspect_ai._util._async import run_coroutine, tg_collect
from inspect_ai._util.file import exists, file
from inspect_ai.log import (
    EvalLog,
    MetadataEdit,
    TagsEdit,
    read_eval_log_async,
)
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.progress import Progress
from rich.text import Text
from rich.tree import Tree
from typing_extensions import Unpack

from inspect_flow._api.list_logs import list_logs
from inspect_flow._cli.store import (
    StoreOptionArgs,
    _resolve_cli_filter,
    filter_options,
    store_options,
)
from inspect_flow._runner.task_log import TaskInfo, unique_task_names
from inspect_flow._types.flow_types import FlowSpec, LogFilter
from inspect_flow._util.console import flow_print, path
from inspect_flow._util.logs import (
    group_logs_by_dir,
    num_valid_samples_async,
)
from inspect_flow._util.path_util import apply_bundle_url_mappings, path_str

logger = getLogger(__name__)


@dataclass
class ListOptions:
    output_format: str = "table"
    log_filter: LogFilter | None = None
    max_count: int | None = None
    oneline: bool = False
    page: bool = True
    provenance: bool = False


def _find_flow_yaml(dir_path: str) -> FlowSpec | None:
    """Load flow.yaml from dir_path if it exists."""
    flow_yaml_path = f"{dir_path}/flow.yaml"
    try:
        if not exists(flow_yaml_path):
            return None
        with file(flow_yaml_path, "r") as f:
            return FlowSpec.model_validate(yaml.safe_load(f.read()))
    except Exception:
        logger.warning(f"Failed to read {flow_yaml_path}", exc_info=True)
        return None


def _viewer_url(log_path: str, spec: FlowSpec) -> str | None:
    """Compute a viewer URL for a log file given the flow spec."""
    if not spec.options or not spec.options.bundle_url_mappings or not spec.log_dir:
        return None
    mappings = spec.options.bundle_url_mappings
    filename = log_path.rsplit("/", 1)[-1]

    def _make_url(dir_path: str) -> str | None:
        mapped = apply_bundle_url_mappings(dir_path, mappings)
        if mapped == dir_path:
            return None
        return f"{mapped.rstrip('/')}/#/logs/{filename}"

    if spec.options.embed_viewer:
        return _make_url(spec.log_dir)

    if spec.options.bundle_dir:
        return _make_url(spec.options.bundle_dir)

    return None


# -- Header reading and qualifier computation ---------------------------------


@dataclass
class _HeaderResult:
    log_path: str
    header: EvalLog
    num_valid_samples: int


async def _read_header(
    log_path: str, on_read: Callable[[], None] | None = None
) -> _HeaderResult | None:
    try:
        header = await read_eval_log_async(log_path, header_only=True)
        valid_samples = await num_valid_samples_async(header)
        return _HeaderResult(log_path, header, valid_samples)
    except Exception:
        return None
    finally:
        if on_read:
            on_read()


def _read_headers(
    log_paths: list[str],
    options: ListOptions,
    progress: Progress | None = None,
) -> dict[str, _HeaderResult]:
    on_read: Callable[[], None] | None = None
    if progress is not None:
        for task in progress.tasks:
            progress.remove_task(task.id)
        task_id = progress.add_task("Reading logs…", total=len(log_paths))
        on_read = partial(progress.advance, task_id)
    results = run_coroutine(
        tg_collect([partial(_read_header, p, on_read) for p in log_paths])
    )
    headers = {r.log_path: r for r in results if r is not None}
    if options.log_filter:
        headers = {p: h for p, h in headers.items() if options.log_filter(h.header)}
    return headers


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
    "cancelled": "gold3",
    "error": "red",
    "started": "cyan",
}


def _duration_str(header_result: _HeaderResult) -> str:
    header = header_result.header
    started = header.stats.started_at
    completed = header.stats.completed_at
    if not started or not completed:
        return ""
    delta = datetime.fromisoformat(completed) - datetime.fromisoformat(started)
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def _date_str(header_result: _HeaderResult) -> str:
    started = header_result.header.stats.started_at
    if not started:
        return ""
    dt = datetime.fromisoformat(started)
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")


def _samples_str(header_result: _HeaderResult) -> str:
    valid_samples = header_result.num_valid_samples
    header = header_result.header
    if header.results:
        return f"{valid_samples}/{header.results.total_samples}"
    total = (header.eval.dataset.samples or 0) * (header.eval.config.epochs or 1)
    return f"{valid_samples}/{total}" if total else ""


@dataclass
class LogEntry:
    header_result: _HeaderResult
    task: str
    qualifier: Text
    viewer_url: str | None = None
    show_provenance: bool = False

    @property
    def log_path(self) -> str:
        return self.header_result.log_path

    @property
    def header(self) -> EvalLog:
        return self.header_result.header


def _compute_entries(
    log_paths: list[str],
    headers: dict[str, _HeaderResult],
    provenance: bool = False,
) -> list[LogEntry]:
    """Compute task name and qualifier for a set of logs in the same directory."""
    valid = [p for p in log_paths if p in headers]
    task_infos = [_eval_log_to_task_info(headers[p].header) for p in valid]
    qualifiers = unique_task_names(task_infos)

    group_dir = valid[0].rsplit("/", 1)[0] if valid else ""
    spec = _find_flow_yaml(group_dir) if group_dir else None

    return [
        LogEntry(
            header_result=headers[p],
            task=name,
            qualifier=qual,
            viewer_url=_viewer_url(p, spec) if spec else None,
            show_provenance=provenance,
        )
        for p, (name, qual) in zip(valid, qualifiers.names, strict=True)
    ]


# -- Formatting ---------------------------------------------------------------


_RIGHT_ALIGN = frozenset({3, 4})  # samples, duration
_COL_PAD = 2
_TREE_GUIDE_WIDTH = 4


def _make_cells(entry: LogEntry, filename_only: bool = False) -> list[Text]:
    log_path = entry.log_path.rsplit("/", 1)[-1] if filename_only else entry.log_path
    status = entry.header.status
    tags = entry.header.tags
    return [
        Text(entry.task),
        entry.qualifier,
        Text(status, style=_STATUS_STYLES.get(status, "")),
        Text(_samples_str(entry.header_result)),
        Text(_duration_str(entry.header_result)),
        Text(", ".join(tags)) if tags else Text(""),
        path(log_path),
        Text(entry.viewer_url or ""),
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
    first = True
    for cols in breaks:
        if all(cells[ci].cell_len == 0 for ci in cols):
            continue
        if not first:
            result.append("\n  ")
        first = False
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


def _describe_edit(edit: TagsEdit | MetadataEdit) -> Text:
    result = Text()
    if isinstance(edit, TagsEdit):
        result.append("tags ")
        items: list[tuple[str, str]] = []
        for t in edit.tags_add:
            items.append((f"+{t}", "green"))
        for t in edit.tags_remove:
            items.append((f"-{t}", "red"))
        for i, (text, style) in enumerate(items):
            if i:
                result.append(", ")
            result.append(text, style=style)
        return result
    result.append("metadata ")
    items = []
    for k, v in (edit.metadata_set or {}).items():
        items.append((f"+{k}={v}", "green"))
    for k in edit.metadata_remove or []:
        items.append((f"-{k}", "red"))
    for i, (text, style) in enumerate(items):
        if i:
            result.append(", ")
        result.append(text, style=style)
    return result


def _render_entry_multiline(entry: LogEntry) -> Text:
    result = Text()
    result.append_text(path(entry.log_path))
    result.append("\n")

    result.append("Task      ", style="grey50")
    result.append(entry.task)
    if entry.qualifier.plain:
        result.append(" ")
        result.append_text(entry.qualifier)
    result.append("\n")

    date = _date_str(entry.header_result)
    if date:
        result.append("Date      ", style="grey50")
        result.append(date)
        duration = _duration_str(entry.header_result)
        if duration:
            result.append(f", {duration}")
        result.append("\n")

    tags = entry.header.tags
    if tags:
        result.append("Tags      ", style="grey50")
        result.append(", ".join(tags))
        result.append("\n")

    if entry.show_provenance:
        for update in entry.header.log_updates or []:
            prov = update.provenance
            ts = prov.timestamp.strftime("%Y-%m-%d %H:%M:%S %z")
            for edit in update.edits:
                result.append("Edit      ", style="grey50")
                result.append_text(_describe_edit(edit))
                result.append("\n")
                result.append("          ", style="grey50")
                result.append(f"{prov.author}, {ts}", style="grey50")
                if prov.reason:
                    result.append(f", {prov.reason}")
                result.append("\n")

    status = entry.header.status
    result.append("Status    ", style="grey50")
    result.append(status, style=_STATUS_STYLES.get(status, ""))
    samples = _samples_str(entry.header_result)
    if samples:
        result.append(", ")
        result.append(samples)
        result.append(" samples")
    result.append("\n")

    if entry.viewer_url:
        result.append("Viewer    ", style="grey50")
        result.append(entry.viewer_url)
        result.append("\n")

    return result


def _render_entries_multiline(entries: list[LogEntry]) -> str:
    if not entries:
        return ""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=2**15)
    for entry in entries:
        console.print(_render_entry_multiline(entry))
    return buf.getvalue()


def _render(entries: list[LogEntry], oneline: bool) -> str:
    if oneline:
        return _render_entries(entries)
    return _render_entries_multiline(entries)


def _entries_renderable(
    entries: list[LogEntry], oneline: bool, width: int, max_lines: int | None = None
) -> RenderableType:
    if oneline:
        rows = [_make_cells(e) for e in entries]
        widths = _col_widths(rows)
        breaks = _break_columns(widths, width)
        formatted = [_format_row(cells, widths, breaks) for cells in rows]
        if max_lines is not None:
            trimmed: list[Text] = []
            total = 0
            for row in formatted:
                lines = row.plain.count("\n") + 1
                if total + lines > max_lines:
                    break
                trimmed.append(row)
                total += lines
            formatted = trimmed
        return Group(*formatted)
    if max_lines is not None:
        renderables: list[Text] = []
        total = 0
        for e in entries:
            rendered = _render_entry_multiline(e)
            lines = rendered.plain.count("\n") + 1
            if total + lines > max_lines:
                break
            renderables.append(rendered)
            total += lines
        return Group(*renderables)
    return Group(*[_render_entry_multiline(e) for e in entries])


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


def _build_tree(
    dir_entries: list[tuple[str, list[LogEntry]]],
    width: int,
    max_lines: int | None = None,
) -> Tree:
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
    breaks = _break_columns(widths, width - tree_indent)

    tree = Tree(prefix or ".")
    nodes: dict[str, Tree] = {}
    idx = 0
    total_lines = 1  # root node
    done = False
    for dir_path, entries in dir_entries:
        if done:
            break
        rel = dir_path[len(prefix) :].lstrip("/") if prefix else dir_path
        parts = [p for p in rel.split("/") if p]
        current: Tree = tree
        built = ""
        for part in parts:
            built = f"{built}/{part}" if built else part
            if built not in nodes:
                nodes[built] = current.add(part)
                total_lines += 1
            current = nodes[built]
        for _ in entries:
            row = _format_row(all_cells[idx], widths, breaks)
            row_lines = row.plain.count("\n") + 1
            if max_lines is not None and total_lines + row_lines > max_lines:
                done = True
                break
            current.add(row)
            total_lines += row_lines
            idx += 1

    return tree


def _format_tree(dir_entries: list[tuple[str, list[LogEntry]]]) -> str:
    return _render_tree(_build_tree(dir_entries, Console().size.width))


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


def _echo_tree(
    dir_groups: list[list[str]],
    options: ListOptions,
    progress: Progress | None = None,
) -> None:
    all_paths = [p for group in dir_groups for p in group]
    headers = _read_headers(all_paths, options, progress=progress)
    if progress:
        progress.stop()

    dir_entries: list[tuple[str, list[LogEntry]]] = []
    count = 0
    for group in dir_groups:
        entries = _compute_entries(group, headers)
        if not entries:
            continue
        if options.max_count is not None:
            entries = entries[: options.max_count - count]
        count += len(entries)
        dir_path = group[0].rsplit("/", 1)[0] if "/" in group[0] else ""
        dir_entries.append((dir_path, entries))
        if options.max_count is not None and count >= options.max_count:
            break

    if not dir_entries:
        flow_print("No logs found")
        return
    output = _format_tree(dir_entries)
    if os.isatty(1) and output.count("\n") > Console().size.height - 1:
        _page_string(output)
    else:
        click.echo(output, nl=False)


# -- Paging -------------------------------------------------------------------


def _process_groups(
    dir_groups: list[list[str]],
    options: ListOptions,
    progress: Progress | None = None,
) -> list[LogEntry]:
    all_paths = [p for group in dir_groups for p in group]
    headers = _read_headers(all_paths, options, progress=progress)
    entries: list[LogEntry] = []
    for group in dir_groups:
        entries.extend(_compute_entries(group, headers, provenance=options.provenance))
    return entries


def _lines_per_entry(oneline: bool) -> int:
    return 1 if oneline else 6


def _echo_logs(
    log_paths: Collection[str],
    options: ListOptions,
    progress: Progress | None = None,
) -> None:
    dir_groups = group_logs_by_dir(log_paths)
    if options.output_format == "tree":
        _echo_tree(dir_groups, options, progress=progress)
        return
    page_size = Console().size.height - 1
    lpe = _lines_per_entry(options.oneline)
    total_entries = min(
        sum(len(g) for g in dir_groups), options.max_count or float("inf")
    )
    if options.page and os.isatty(1) and total_entries * lpe > page_size:
        _paged_output(dir_groups, page_size, options, progress=progress)
    else:
        entries = _process_groups(dir_groups, options, progress=progress)
        if options.max_count is not None:
            entries = entries[: options.max_count]
        if progress:
            progress.stop()
        if not entries:
            flow_print("No logs found")
            return
        click.echo(_render(entries, options.oneline), nl=False)


def _paged_output(
    dir_groups: list[list[str]],
    page_size: int,
    options: ListOptions,
    progress: Progress | None = None,
) -> None:
    env = os.environ.copy()
    env["LESS"] = env.get("LESS", "") + " -RX"
    pager = env.get("PAGER", "less")
    proc = subprocess.Popen(pager.split(), stdin=subprocess.PIPE, env=env)
    assert proc.stdin
    lpe = _lines_per_entry(options.oneline)
    batch_entries = max(1, page_size // lpe)
    emitted = 0
    try:
        pending: list[list[str]] = []
        pending_count = 0
        first = True
        for group in dir_groups:
            pending.append(group)
            pending_count += len(group)
            if pending_count >= batch_entries:
                entries = _process_groups(
                    pending, options, progress=progress if first else None
                )
                if first and progress:
                    progress.stop()
                    progress = None
                first = False
                if options.max_count is not None:
                    entries = entries[: options.max_count - emitted]
                emitted += len(entries)
                proc.stdin.write(_render(entries, options.oneline).encode())
                proc.stdin.flush()
                pending = []
                pending_count = 0
                if options.max_count is not None and emitted >= options.max_count:
                    break
        if pending:
            entries = _process_groups(
                pending, options, progress=progress if first else None
            )
            if first and progress:
                progress.stop()
            if options.max_count is not None:
                entries = entries[: options.max_count - emitted]
            emitted += len(entries)
            proc.stdin.write(_render(entries, options.oneline).encode())
            proc.stdin.flush()
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
        proc.wait()
    if emitted == 0:
        flow_print("No logs found")


# -- Live output --------------------------------------------------------------


def _compute_renderable(
    log_dir: str | None,
    store: str,
    since: str | None,
    until: str | None,
    options: ListOptions,
    console: Console,
) -> RenderableType:
    log_paths = list_logs(log_dir=log_dir, store=store, since=since, until=until)
    if not log_paths:
        return Text("No logs found")
    log_paths_str = [path_str(p) for p in log_paths]
    dir_groups = group_logs_by_dir(log_paths_str)

    page_lines = console.size.height - 2

    if options.output_format == "tree":
        all_paths = [p for group in dir_groups for p in group]
        headers = _read_headers(all_paths, options)
        dir_entries: list[tuple[str, list[LogEntry]]] = []
        count = 0
        for group in dir_groups:
            entries = _compute_entries(group, headers)
            if not entries:
                continue
            if options.max_count is not None:
                entries = entries[: options.max_count - count]
            count += len(entries)
            dir_path = group[0].rsplit("/", 1)[0] if "/" in group[0] else ""
            dir_entries.append((dir_path, entries))
            if options.max_count is not None and count >= options.max_count:
                break
        if not dir_entries:
            return Text("No logs found")
        return _build_tree(dir_entries, console.size.width, max_lines=page_lines)

    entries = _process_groups(dir_groups, options)
    if options.max_count is not None:
        entries = entries[: options.max_count]
    if not entries:
        return Text("No logs found")
    return _entries_renderable(
        entries, options.oneline, console.size.width, max_lines=page_lines
    )


def _live_output(
    log_dir: str | None,
    store: str,
    since: str | None,
    until: str | None,
    options: ListOptions,
    interval: int,
) -> None:
    console = Console()
    renderable = _compute_renderable(log_dir, store, since, until, options, console)
    with Live(renderable, console=console, refresh_per_second=1) as live:
        try:
            while True:
                time.sleep(interval)
                live.update(
                    _compute_renderable(log_dir, store, since, until, options, console)
                )
        except KeyboardInterrupt:
            pass


# -- CLI commands -------------------------------------------------------------


def _chain(base: LogFilter | None, new: LogFilter) -> LogFilter:
    if base is None:
        return new

    def combined(log: EvalLog) -> bool:
        return base(log) and new(log)

    return combined


@click.group("list")
def list_command() -> None:
    """CLI command to list flow entities."""
    pass


class _MaxCountCommand(click.Command):
    """Rewrites bare -<number> args to --max-count=<number>."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        rewritten: list[str] = []
        for arg in args:
            if len(arg) > 1 and arg[0] == "-" and arg[1:].isdigit():
                rewritten.append(f"--max-count={arg[1:]}")
            else:
                rewritten.append(arg)
        return super().parse_args(ctx, rewritten)


@list_command.command(
    "log",
    cls=_MaxCountCommand,
    help="List logs, sorted by timestamp extracted from log file name. If PATH is not provided, falls back to the default store (--store auto).",
)
@store_options
@filter_options
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "tree"]),
    default="table",
    help="Output format",
)
@click.option(
    "--oneline",
    is_flag=True,
    default=False,
    help="Show each log on a single line (compact table format).",
)
@click.option(
    "--provenance",
    is_flag=True,
    default=False,
    help="Show provenance (edit history) for each log. Only displayed in multiline mode.",
)
@click.option(
    "--no-page",
    "no_page",
    is_flag=True,
    default=False,
    help="Disable paged output.",
)
@click.option(
    "-n",
    "--max-count",
    "max_count",
    type=int,
    default=None,
    help="Limit output to N logs. Also accepts -N (e.g. -5).",
)
@click.option(
    "--task",
    "tasks",
    multiple=True,
    metavar="PATTERN",
    help="Only show logs whose task name matches PATTERN (glob). May be repeated.",
)
@click.option(
    "--model",
    "models",
    multiple=True,
    metavar="PATTERN",
    help="Only show logs whose model matches PATTERN (glob). May be repeated.",
)
@click.option(
    "--tag",
    "tags",
    multiple=True,
    metavar="PATTERN",
    help="Only show logs with a tag matching PATTERN (glob). May be repeated.",
)
@click.option(
    "--status",
    "statuses",
    multiple=True,
    type=click.Choice(["success", "error", "cancelled", "started"]),
    help="Only show logs with this status. May be repeated.",
)
@click.option(
    "--live",
    "live_interval",
    type=int,
    default=None,
    is_flag=False,
    flag_value=10,
    help="Refresh display every N seconds (default: 10).",
)
@click.option(
    "--since",
    "--after",
    "since",
    default=None,
    metavar="DATE",
    help="Only show logs whose filename timestamp is at or after DATE. Date strings like `'2024-01-15'` resolve to midnight; relative expressions like `'today'` resolve to the current time.",
)
@click.option(
    "--until",
    "--before",
    "until",
    default=None,
    metavar="DATE",
    help="Only show logs whose filename timestamp is at or before DATE. Date strings like `'2024-06-01'` resolve to midnight; relative expressions like `'yesterday'` resolve to the current time minus one day.",
)
@click.argument("path", required=False, default=None)
def list_log(
    path: str | None,
    output_format: str,
    oneline: bool,
    provenance: bool,
    no_page: bool,
    max_count: int | None,
    tasks: tuple[str, ...],
    models: tuple[str, ...],
    tags: tuple[str, ...],
    statuses: tuple[str, ...],
    live_interval: int | None,
    since: str | None,
    until: str | None,
    filter_name: tuple[str, ...],
    exclude_name: str | None,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    log_filter = _resolve_cli_filter(filter_name, exclude_name)
    if tasks:
        task_patterns = tasks
        log_filter = _chain(
            log_filter,
            lambda log: any(fnmatch.fnmatch(log.eval.task, p) for p in task_patterns),
        )
    if models:
        model_patterns = models
        log_filter = _chain(
            log_filter,
            lambda log: any(fnmatch.fnmatch(log.eval.model, p) for p in model_patterns),
        )
    if tags:
        tag_patterns = tags
        log_filter = _chain(
            log_filter,
            lambda log: any(
                fnmatch.fnmatch(t, p) for t in log.tags for p in tag_patterns
            ),
        )
    if statuses:
        status_set = set(statuses)
        log_filter = _chain(log_filter, lambda log: log.status in status_set)
    options = ListOptions(
        output_format=output_format,
        log_filter=log_filter,
        max_count=max_count,
        oneline=oneline,
        page=not no_page,
        provenance=provenance,
    )
    store = kwargs.get("store") or "auto"
    if live_interval is not None:
        _live_output(path, store, since, until, options, live_interval)
        return
    progress = Progress(transient=True)
    progress.add_task("Listing logs…", total=None)
    progress.start()
    log_paths = list_logs(log_dir=path, store=store, since=since, until=until)
    if not log_paths:
        progress.stop()
        flow_print("No logs found")
        return
    log_paths = [path_str(p) for p in log_paths]
    _echo_logs(log_paths, options, progress=progress)
