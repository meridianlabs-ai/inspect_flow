import io
import os
import re
import subprocess
from collections.abc import Collection
from dataclasses import dataclass
from functools import partial

import click
from inspect_ai._util._async import run_coroutine, tg_collect
from inspect_ai.log import EvalLog, list_eval_logs, read_eval_log_async
from rich.console import Console
from rich.text import Text
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


async def _read_header(log_path: str) -> tuple[str, EvalLog | None]:
    try:
        return log_path, await read_eval_log_async(log_path, header_only=True)
    except Exception:
        return log_path, None


def _read_headers(log_paths: list[str]) -> dict[str, EvalLog]:
    results = run_coroutine(tg_collect([partial(_read_header, p) for p in log_paths]))
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


def _compute_entries(
    log_paths: list[str], headers: dict[str, EvalLog]
) -> list[LogEntry]:
    """Compute task name and qualifier for a set of logs in the same directory."""
    valid = [p for p in log_paths if p in headers]
    task_infos = [_eval_log_to_task_info(headers[p]) for p in valid]
    qualifiers = unique_task_names(task_infos)

    entries = [
        LogEntry(p, name, qual, headers[p].status, _samples_str(headers[p]))
        for p, (name, qual) in zip(valid, qualifiers.names, strict=True)
    ]
    valid_set = set(valid)
    for p in log_paths:
        if p not in valid_set:
            entries.append(LogEntry(p, "", Text(), "", ""))
    return entries


# -- Formatting ---------------------------------------------------------------


def _format_entries(entries: list[LogEntry]) -> str:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    task_width = max((len(e.task) for e in entries), default=0)
    qual_width = max((e.qualifier.cell_len for e in entries), default=0)
    status_width = max((len(e.status) for e in entries), default=0)
    samples_width = max((len(e.samples) for e in entries), default=0)
    for entry in entries:
        line = Text()
        line.append(entry.task.ljust(task_width))
        if qual_width > 0:
            line.append("  ")
            line.append_text(entry.qualifier)
            padding = qual_width - entry.qualifier.cell_len
            if padding > 0:
                line.append(" " * padding)
        if status_width > 0:
            line.append("  ")
            style = _STATUS_STYLES.get(entry.status, "")
            line.append(entry.status.ljust(status_width), style=style)
        if samples_width > 0:
            line.append("  ")
            line.append(entry.samples.rjust(samples_width))
        line.append("  ")
        line.append_text(path(entry.log_path))
        console.print(line)
    return buf.getvalue()


# -- Paging -------------------------------------------------------------------


def _process_groups(dir_groups: list[list[str]]) -> list[LogEntry]:
    entries: list[LogEntry] = []
    for group in dir_groups:
        headers = _read_headers(group)
        entries.extend(_compute_entries(group, headers))
    return entries


def _echo_logs(log_paths: Collection[str]) -> None:
    dir_groups = _group_by_dir(log_paths)
    total = sum(len(g) for g in dir_groups)
    page_size = Console().size.height - 1
    if total <= page_size:
        click.echo(_format_entries(_process_groups(dir_groups)), nl=False)
    else:
        _paged_output(dir_groups, page_size)


def _paged_output(dir_groups: list[list[str]], page_size: int) -> None:
    env = os.environ.copy()
    env["LESS"] = env.get("LESS", "") + " -RX"
    pager = env.get("PAGER", "less")
    proc = subprocess.Popen(pager.split(), stdin=subprocess.PIPE, env=env)
    assert proc.stdin
    try:
        batch: list[LogEntry] = []
        for group in dir_groups:
            headers = _read_headers(group)
            batch.extend(_compute_entries(group, headers))
            if len(batch) >= page_size:
                proc.stdin.write(_format_entries(batch).encode())
                proc.stdin.flush()
                batch = []
        if batch:
            proc.stdin.write(_format_entries(batch).encode())
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
@click.argument("path", required=False, default=None)
def list_log(path: str | None, **kwargs: Unpack[StoreOptionArgs]) -> None:
    if path is not None:
        log_infos = list_eval_logs(log_dir=path, recursive=True)
        if not log_infos:
            flow_print("No logs found in", path)
            return
        _echo_logs([info.name for info in log_infos])
    else:
        flow_store = init_store(quiet=True, **kwargs)
        if not flow_store:
            return
        log_files = flow_store.get_logs()
        if not log_files:
            flow_print("No logs in store")
            return
        _echo_logs(log_files)
