from collections.abc import Callable
from typing import Literal, TypeVar

import click
from click import Context, HelpFormatter
from rich.text import Text
from rich.tree import Tree
from typing_extensions import TypedDict, Unpack

from inspect_flow._cli.options import output_options
from inspect_flow._store.store import (
    FlowStore,
    delete_store,
    resolve_store_path,
    store_exists,
    store_factory,
)
from inspect_flow._util.console import console, flow_print, path, quantity
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
    f = output_options(f)
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
        flow_print(
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
        flow_print("\n[blue][DRY RUN][/blue] Preview mode - logs will be imported\n")

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
        "PREFIX...": "One or more prefixes to match against log paths [optional]"
    },
)
@store_options
@click.argument("prefix", nargs=-1, required=False, envvar="INSPECT_FLOW_STORE_PREFIX")
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    default=False,
    help="Search directories recursively for logs",
    envvar="INSPECT_FLOW_STORE_RECURSIVE",
)
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
    prefix: tuple[str, ...],
    recursive: bool,
    missing: bool,
    dry_run: bool,
    verbose: bool,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    if not prefix and not missing:
        raise click.UsageError("Either prefix or --missing must be specified.")
    if prefix and missing:
        raise click.UsageError("Cannot specify both prefix and --missing.")
    flow_store = init_store(**kwargs)
    if flow_store:
        flow_store.remove_log_prefix(
            list(prefix),
            missing=missing,
            recursive=recursive,
            dry_run=dry_run,
            verbose=verbose,
        )


ListFormat = Literal["flat", "tree"]


def _echo_logs(flow_store: FlowStore, format: ListFormat = "flat") -> None:
    log_files = flow_store.get_logs()
    if not log_files:
        flow_print("\nNo logs in store")
        return
    if format == "tree":
        _echo_logs_tree(sorted(log_files))
    else:
        for log_file in sorted(log_files):
            flow_print(path(log_file))


def _echo_logs_tree(log_files: list[str]) -> None:
    tree = Tree("", hide_root=True)
    nodes: dict[str, Tree] = {}
    for log_file in log_files:
        display = path(log_file)
        parts = display.plain.split("/")
        dirs = parts[:-1]

        current_path = ""
        parent = tree
        for part in dirs:
            current_path = f"{current_path}/{part}" if current_path else part
            if current_path not in nodes:
                nodes[current_path] = parent.add(Text(part, style="magenta"))
            parent = nodes[current_path]

        filename = parts[-1]
        parent.add(path(filename))

    console.print(tree)


@store_command.command("info", help="Print store information")
@store_options
def store_info(**kwargs: Unpack[StoreOptionArgs]) -> None:
    flow_store = init_store(**kwargs)
    if not flow_store:
        return
    logs = flow_store.get_logs()
    log_dirs = {log.rsplit("/", 1)[0] for log in logs}
    flow_print("Path:    ", path(flow_store.store_path))
    flow_print("Logs:    ", quantity(len(logs), "log"))
    flow_print("Log dirs:", quantity(len(log_dirs), "log dir"))
    flow_print("Version: ", flow_store.version)


@store_command.command("delete", help="Delete the flow store")
@store_options
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def store_delete(yes: bool, **kwargs: Unpack[StoreOptionArgs]) -> None:
    log_level = kwargs.get("log_level", DEFAULT_LOG_LEVEL)
    init_flow_logging(log_level)
    store_path = resolve_store_path(kwargs.get("store"))
    if not store_exists(store_path):
        flow_print("Store not found at", path(store_path), format="error")
        return
    if not yes:
        click.confirm(
            f"Are you sure you want to delete the store at {store_path}?",
            abort=True,
        )
    delete_store(store_path)
    flow_print("Deleted store at", path(store_path), format="success")


@store_command.command("list", help="List logs and log directories in the store")
@store_options
@click.option(
    "--format",
    "format",
    type=click.Choice(["flat", "tree"]),
    default="flat",
    help="Output format: tree, flat",
    envvar="INSPECT_FLOW_STORE_LIST_FORMAT",
)
def store_list(format: str, **kwargs: Unpack[StoreOptionArgs]) -> None:
    assert format in ("flat", "tree")
    flow_store = init_store(**kwargs)
    if flow_store:
        _echo_logs(flow_store, format=format)
