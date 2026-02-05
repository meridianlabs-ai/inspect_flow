from collections.abc import Callable
from typing import TypeVar

import click
from click import Context, HelpFormatter
from typing_extensions import TypedDict, Unpack

from inspect_flow._cli.options import log_level_option
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._util.console import path, print
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.logs import copy_all_logs


class ArgumentsHelpCommand(click.Command):
    """Command that displays arguments help section aligned with Options."""

    def __init__(
        self,
        *args: object,
        arguments_help: dict[str, str] | None = None,
        **kwargs: object,
    ) -> None:
        self.arguments_help = arguments_help or {}
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        if self.arguments_help:
            self.format_arguments(formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_arguments(self, formatter: HelpFormatter) -> None:
        with formatter.section("Arguments"):
            formatter.write_dl(list(self.arguments_help.items()))


F = TypeVar("F", bound=Callable[..., object])


def store_options(f: F) -> F:
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
        help="Path to the store directory",
        envvar="INSPECT_FLOW_STORE",
    )(f)
    return f


def log_paths_arguments(*, required: bool = True) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        func = click.argument(
            "path",
            nargs=-1,
            type=click.Path(
                file_okay=True,
                dir_okay=True,
                writable=True,
                readable=True,
                resolve_path=False,
            ),
            required=required,
            envvar="INSPECT_FLOW_STORE_PATH",
        )(func)
        func = click.option(
            "--recursive",
            "-r",
            is_flag=True,
            default=False,
            help="Search directories recursively for logs",
            envvar="INSPECT_FLOW_STORE_RECURSIVE",
        )(func)

        return func

    return decorator


class StoreOptionArgs(TypedDict, total=False):
    log_level: str
    store: str | None


def init_store(
    create: bool = False, **kwargs: Unpack[StoreOptionArgs]
) -> FlowStore | None:
    log_level = kwargs.get("log_level", DEFAULT_LOG_LEVEL)
    init_flow_logging(log_level)
    store_location = kwargs.get("store") or "auto"
    flow_store = store_factory(store_location, base_dir=".", create=create)
    if not flow_store:
        print(
            "Error: Store not found at",
            path(store_location),
            "Run 'flow store import' to create the store and import logs.",
            format="error",
        )
    return flow_store


@click.group("store", help="Manage the flow store")
def store_command() -> None:
    """CLI command group for flow store operations."""
    pass


@store_command.command(
    "import",
    cls=ArgumentsHelpCommand,
    arguments_help={
        "PATH...": "One or more paths to log files or directories [required]"
    },
)
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
    help="Copy logs from this directory to PATH before importing.",
    envvar="INSPECT_FLOW_STORE_IMPORT_COPY_FROM",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be imported without making changes",
    envvar="INSPECT_FLOW_STORE_IMPORT_DRY_RUN",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print paths of files being added",
)
def store_import(
    path: tuple[str, ...],
    recursive: bool,
    copy_from: str | None,
    dry_run: bool,
    verbose: bool,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    if dry_run:
        print("\n[blue][DRY RUN][/blue] Preview mode - logs will be imported\n")

    flow_store = init_store(create=True, **kwargs)
    if not flow_store:
        return
    if copy_from:
        if recursive:
            raise click.UsageError("Cannot use --copy-from with --recursive")
        if len(path) != 1:
            raise click.UsageError(
                "When using --copy-from, exactly one PATH must be specified"
            )
        copy_all_logs(src_dir=copy_from, dest_dir=path[0], dry_run=dry_run)
    flow_store.import_log_path(
        list(path), recursive=recursive, dry_run=dry_run, verbose=verbose
    )


@store_command.command(
    "remove",
    cls=ArgumentsHelpCommand,
    arguments_help={
        "PATH...": "One or more paths to log files or directories [optional]"
    },
)
@store_options
@log_paths_arguments(required=False)
@click.option(
    "--missing",
    is_flag=True,
    default=False,
    help="Remove logs that no longer exist on file system",
    envvar="INSPECT_FLOW_STORE_REMOVE_MISSING",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be removed without making changes",
    envvar="INSPECT_FLOW_STORE_REMOVE_DRY_RUN",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print paths of files being removed",
)
def store_remove(
    path: tuple[str, ...],
    recursive: bool,
    missing: bool,
    dry_run: bool,
    verbose: bool,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    if not path and not missing:
        raise click.UsageError("Either path or --missing must be specified.")
    if path and missing:
        raise click.UsageError("Cannot specify both path and --missing.")
    flow_store = init_store(**kwargs)
    if flow_store:
        flow_store.remove_log_path(
            list(path),
            missing=missing,
            recursive=recursive,
            dry_run=dry_run,
            verbose=verbose,
        )


def _echo_logs(flow_store: FlowStore) -> None:
    log_files = flow_store.get_logs()
    if not log_files:
        print("\nNo logs in store")
        return
    for log_file in sorted(log_files):
        print(path(log_file))


@store_command.command("list", help="List logs and log directories in the store")
@store_options
def store_list(**kwargs: Unpack[StoreOptionArgs]) -> None:
    flow_store = init_store(**kwargs)
    if flow_store:
        _echo_logs(flow_store)
