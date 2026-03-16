import click

from inspect_flow._cli.store import init_store
from inspect_flow._util.console import console, flow_print, path


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
    with console.pager(styles=True):
        for log_file in sorted(log_files):
            console.print(path(log_file))
