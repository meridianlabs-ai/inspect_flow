import io
import os
import re
import subprocess
from collections.abc import Collection
from functools import partial

import click
from inspect_ai._util._async import run_coroutine, tg_collect
from inspect_ai.log import list_eval_logs, read_eval_log_async
from rich.console import Console
from rich.text import Text
from typing_extensions import Unpack

from inspect_flow._cli.store import StoreOptionArgs, init_store, store_options
from inspect_flow._util.console import flow_print, path

_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T")


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


async def _read_task(log_path: str) -> tuple[str, str]:
    try:
        header = await read_eval_log_async(log_path, header_only=True)
        return log_path, header.eval.task
    except Exception:
        return log_path, ""


def _read_tasks(log_paths: list[str]) -> dict[str, str]:
    results = run_coroutine(tg_collect([partial(_read_task, p) for p in log_paths]))
    return dict(results)


def _format_batch(log_paths: list[str], tasks: dict[str, str]) -> str:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    task_width = max((len(tasks.get(p, "")) for p in log_paths), default=0)
    for log_path in log_paths:
        task = tasks.get(log_path, "")
        line = Text()
        line.append(task.ljust(task_width))
        line.append("  ")
        line.append_text(path(log_path))
        console.print(line)
    return buf.getvalue()


def _echo_logs(log_paths: list[str]) -> None:
    page_size = Console().size.height - 1
    if len(log_paths) <= page_size:
        tasks = _read_tasks(log_paths)
        click.echo(_format_batch(log_paths, tasks), nl=False)
    else:
        _paged_output(log_paths, page_size)


def _paged_output(log_paths: list[str], page_size: int) -> None:
    env = os.environ.copy()
    env["LESS"] = env.get("LESS", "") + " -RX"
    pager = env.get("PAGER", "less")
    proc = subprocess.Popen(pager.split(), stdin=subprocess.PIPE, env=env)
    assert proc.stdin
    try:
        for i in range(0, len(log_paths), page_size):
            batch = log_paths[i : i + page_size]
            tasks = _read_tasks(batch)
            proc.stdin.write(_format_batch(batch, tasks).encode())
            proc.stdin.flush()
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
        proc.wait()


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
        _echo_logs(_sort_logs([info.name for info in log_infos]))
    else:
        flow_store = init_store(quiet=True, **kwargs)
        if not flow_store:
            return
        log_files = flow_store.get_logs()
        if not log_files:
            flow_print("No logs in store")
            return
        _echo_logs(_sort_logs(log_files))
