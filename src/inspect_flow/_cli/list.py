import io
import os

import click
from rich.console import Console

from inspect_flow._cli.store import init_store
from inspect_flow._util.console import flow_print, path


@click.group("list")
def list_command() -> None:
    """CLI command to list flow entities."""
    pass


@list_command.command("log", help="List logs")
def list_log() -> None:
    flow_store = init_store(quiet=True)
    if not flow_store:
        return
    log_files = flow_store.get_logs()
    if not log_files:
        flow_print("No logs in store")
        return
    buf = io.StringIO()
    pager_console = Console(file=buf, force_terminal=True)
    for log_file in sorted(log_files):
        pager_console.print(path(log_file))
    output = buf.getvalue()
    if output.count("\n") > Console().size.height:
        os.environ["LESS"] = os.environ.get("LESS", "") + " -RX"
        click.echo_via_pager(output)
    else:
        click.echo(output, nl=False)
