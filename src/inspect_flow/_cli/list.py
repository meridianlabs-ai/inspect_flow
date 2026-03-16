import io
import os
import re
from collections.abc import Collection

import click
from inspect_ai.log import list_eval_logs
from rich.console import Console
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


@click.group("list")
def list_command() -> None:
    """CLI command to list flow entities."""
    pass


def _pager_echo(log_files: Collection[str]) -> None:
    sorted_logs = _sort_logs(log_files)
    buf = io.StringIO()
    pager_console = Console(file=buf, force_terminal=True)
    for log_file in sorted_logs:
        pager_console.print(path(log_file))
    output = buf.getvalue()
    if output.count("\n") > Console().size.height:
        os.environ["LESS"] = os.environ.get("LESS", "") + " -RX"
        click.echo_via_pager(output)
    else:
        click.echo(output, nl=False)


@list_command.command("log", help="List logs")
@store_options
@click.argument("path", required=False, default=None)
def list_log(path: str | None, **kwargs: Unpack[StoreOptionArgs]) -> None:
    if path is not None:
        log_infos = list_eval_logs(log_dir=path, recursive=True)
        if not log_infos:
            flow_print("No logs found in", path)
            return
        _pager_echo([info.name for info in log_infos])
    else:
        flow_store = init_store(quiet=True, **kwargs)
        if not flow_store:
            return
        log_files = flow_store.get_logs()
        if not log_files:
            flow_print("No logs in store")
            return
        _pager_echo(log_files)
