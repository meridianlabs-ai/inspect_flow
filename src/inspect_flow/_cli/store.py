import click
from typing_extensions import TypedDict, Unpack

from inspect_flow._cli.options import log_level_option
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.logs import copy_all_logs
from inspect_flow._util.path_util import path_str


def store_options(f):
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
            help="Recursively search sub directories for logs.",
            envvar="INSPECT_FLOW_STORE_RECURSIVE",
        )(func)

        return func

    return decorator


class StoreOptionArgs(TypedDict, total=False):
    log_level: str
    store: str | None


def init_store(**kwargs: Unpack[StoreOptionArgs]) -> FlowStore:
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


@store_command.command("import", help="Import existing logs to the store")
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


@store_command.command("remove", help="Remove logs from the store")
@store_options
@log_paths_arguments(required=False)
@click.option(
    "--missing",
    is_flag=True,
    default=False,
    help="Remove logs that are missing from the file system.",
    envvar="INSPECT_FLOW_STORE_REMOVE_MISSING",
)
def store_remove(
    log_paths: tuple[str, ...],
    recursive: bool,
    missing: bool,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    if not log_paths and not missing:
        raise click.UsageError("Either log_paths or --missing must be specified.")
    if log_paths and missing:
        raise click.UsageError("Cannot specify both log_paths and --missing.")
    flow_store = init_store(**kwargs)
    flow_store.remove_log_path(list(log_paths), missing=missing, recursive=recursive)


def _echo_logs(flow_store: FlowStore) -> None:
    log_files = flow_store.get_logs()
    for log_file in sorted(log_files):
        click.echo(path_str(log_file))


@store_command.command("list", help="List logs and log directories in the store")
@store_options
def store_list(**kwargs: Unpack[StoreOptionArgs]) -> None:
    flow_store = init_store(**kwargs)
    return _echo_logs(flow_store)
