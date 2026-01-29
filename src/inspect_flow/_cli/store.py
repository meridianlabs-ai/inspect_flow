import click
from inspect_ai._util.file import basename, dirname
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
        type=click.Path(
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
            resolve_path=False,
        ),
        default=None,
        help="Path to the store directory. Defaults to the default store location.",
        envvar="INSPECT_FLOW_STORE",
    )(f)
    return f


def log_paths_arguments(*, required: bool = True):
    def decorator(func):
        func = click.argument(
            "log_paths",
            nargs=-1,
            type=click.Path(
                file_okay=True,
                dir_okay=True,
                writable=True,
                readable=True,
                resolve_path=False,
            ),
            required=required,
            envvar="INSPECT_FLOW_STORE_LOG_PATHS",
        )(func)
        func = click.option(
            "--recursive",
            "-r",
            is_flag=True,
            default=False,
            help="Recursively search for log directories.",
            envvar="INSPECT_FLOW_STORE_RECURSIVE",
        )(func)

        return func

    return decorator


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


@store_command.command("import", help="Import existing log directories to the store")
@store_options
@log_paths_arguments()
@click.option(
    "--copy-from",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=False,
    ),
    help="Copy logs to the directory being imported.",
    envvar="INSPECT_FLOW_STORE_IMPORT_COPY_FROM",
)
def store_import(
    log_paths: tuple[str, ...],
    recursive: bool,
    copy_from: str | None,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    """Import existing log directories to the flow store."""
    flow_store = init_store(**kwargs)
    if copy_from:
        if recursive:
            raise click.UsageError(
                "Cannot use --recursive with --copy-from. Recursive finds existing log directories."
            )
        if len(log_paths) != 1:
            raise click.UsageError(
                "When using --copy-from, exactly one log_path must be specified as the destination."
            )
        copy_all_logs(src_dir=copy_from, dest_dir=log_paths[0])
    flow_store.import_log_path(list(log_paths), recursive=recursive)


@store_command.command("remove", help="Remove log directories from the store")
@store_options
@log_paths_arguments(required=False)
@click.option(
    "--missing",
    is_flag=True,
    default=False,
    help="Remove log paths that are missing from the file system.",
    envvar="INSPECT_FLOW_STORE_REMOVE_MISSING",
)
def store_remove(
    log_paths: tuple[str, ...],
    recursive: bool,
    missing: bool,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    """Remove log paths from the flow store."""
    if not log_paths and not missing:
        raise click.UsageError("Either log_paths or --missing must be specified.")
    if log_paths and missing:
        raise click.UsageError("Cannot specify both log_paths and --missing.")
    flow_store = init_store(**kwargs)
    flow_store.remove_log_path(list(log_paths), missing=missing, recursive=recursive)


@store_command.command("list", help="List log paths in the store")
@store_options
@click.option(
    "--type",
    type=click.Choice(["logs", "dirs", "all"], case_sensitive=False),
    default="all",
    help="Type of log paths to list",
    envvar="INSPECT_FLOW_STORE_LIST_TYPE",
)
def store_list(type: str, **kwargs: Unpack[StoreOptionArgs]) -> None:
    flow_store = init_store(**kwargs)
    if type == "logs":
        log_files = flow_store.get_logs()
        for log_file in sorted(log_files):
            click.echo(path_str(log_file))
        return

    log_dirs = flow_store.get_log_dirs()
    if log_dirs:
        dir_to_logs: dict[str, list[str]] = {}
        if type == "all":
            log_files = flow_store.get_logs()
            for log_file in log_files:
                dir = dirname(log_file)
                if dir in log_dirs:
                    dir_to_logs.setdefault(dir, []).append(log_file)
                else:
                    dir_to_logs.setdefault("", []).append(log_file)
        for log_dir in sorted(log_dirs):
            click.echo(path_str(log_dir))
            if type == "all":
                log_files = dir_to_logs.get(log_dir, [])
                for log_file in sorted(log_files):
                    click.echo("    " + basename(log_file))
        if unparented := dir_to_logs.get(""):
            click.echo("logs not in imported directories:")
            for log_file in sorted(unparented):
                click.echo("    " + basename(log_file))


@store_command.command(
    "refresh", help="Refresh the store to reflect the current file system state"
)
@store_options
def store_refresh(**kwargs: Unpack[StoreOptionArgs]) -> None:
    """Refresh the flow store to reflect the current state of the file system."""
    flow_store = init_store(**kwargs)
    flow_store.refresh()
