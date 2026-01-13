import click
from inspect_ai._util.file import dirname
from typing_extensions import TypedDict, Unpack

from inspect_flow._cli.options import log_level_option
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.logs import copy_all_logs
from inspect_flow._util.path_util import path_str


def store_options(f):
    """Shared options for store commands."""
    f = log_level_option(f)
    f = click.option(
        "--store",
        "-s",
        type=str,
        default=None,
        help="Path to the store directory. Defaults to the default store location.",
        envvar="INSPECT_FLOW_STORE",
    )(f)
    return f


def log_dirs_argument(f):
    f = click.argument(
        "log_dirs",
        nargs=-1,
        required=True,
        envvar="INSPECT_FLOW_STORE_LOG_DIRS",
    )(f)
    return f


class StoreOptionArgs(TypedDict, total=False):
    log_level: str
    store: str | None


def init_store(**kwargs: Unpack[StoreOptionArgs]) -> FlowStore:
    """Initialize logging and return a FlowStore instance."""
    log_level = kwargs.get("log_level", DEFAULT_LOG_LEVEL)
    init_flow_logging(log_level)
    store_location = kwargs.get("store") or "auto"
    flow_store = store_factory(store_location, base_dir=".")
    assert flow_store is not None
    return flow_store


@click.group("store", help="Manage the flow store")
def store_command() -> None:
    """CLI command group for flow store operations."""
    pass


@store_command.command("add", help="Add log directories to the store")
@store_options
@log_dirs_argument
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    default=False,
    help="Recursively search for log directories.",
    envvar="INSPECT_FLOW_STORE_ADD_RECURSIVE",
)
@click.option(
    "--copy-from",
    type=str,
    help="Recursively search for log directories.",
    envvar="INSPECT_FLOW_STORE_ADD_COPY_FROM",
)
def store_add(
    log_dirs: tuple[str, ...],
    recursive: bool,
    copy_from: str | None,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    """Add log directories to the flow store."""
    flow_store = init_store(**kwargs)
    if copy_from:
        if recursive:
            raise click.UsageError(
                "Cannot use --recursive with --copy-from. Recursive finds existing log directories."
            )
        if len(log_dirs) != 1:
            raise click.UsageError(
                "When using --copy-from, exactly one log_dir must be specified as the destination."
            )
        copy_all_logs(src_dir=copy_from, dest_dir=log_dirs[0])
    flow_store.add_log_dir(list(log_dirs), recursive=recursive)


@store_command.command("remove", help="Remove log directories from the store")
@store_options
@log_dirs_argument
def store_remove(log_dirs: tuple[str, ...], **kwargs: Unpack[StoreOptionArgs]) -> None:
    """Remove log directories from the flow store."""
    flow_store = init_store(**kwargs)
    flow_store.remove_log_dir(list(log_dirs))


@store_command.command("list", help="List log directories in the store")
@store_options
@click.option(
    "--logs",
    is_flag=True,
    default=False,
    help="List logs in the store.",
    envvar="INSPECT_FLOW_STORE_LIST_LOGS",
)
def store_list(logs: bool, **kwargs: Unpack[StoreOptionArgs]) -> None:
    """List all log directories in the flow store."""
    flow_store = init_store(**kwargs)
    log_dirs = flow_store.get_log_dirs()
    if log_dirs:
        dir_to_logs: dict[str, list[str]] = {}
        if logs:
            log_files = flow_store.get_logs()
            for log_file in log_files:
                dir_to_logs.setdefault(dirname(log_file), []).append(log_file)
        for log_dir in sorted(log_dirs):
            click.echo(path_str(log_dir))
            if logs:
                log_files = dir_to_logs.get(log_dir, [])
                for log_file in sorted(log_files):
                    click.echo(path_str(log_file))
    else:
        click.echo("No log directories in the store.")


@store_command.command(
    "refresh", help="Refresh the store to reflect the current file system state"
)
@store_options
def store_refresh(**kwargs: Unpack[StoreOptionArgs]) -> None:
    """Refresh the flow store to reflect the current state of the file system."""
    flow_store = init_store(**kwargs)
    flow_store.refresh()
