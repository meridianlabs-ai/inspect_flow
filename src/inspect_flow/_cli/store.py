from collections.abc import Callable
from typing import Any, Literal, TypeVar

import click
from click import Context, HelpFormatter
from rich.text import Text
from rich.tree import Tree
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    OutputOptionArgs,
    init_output,
    output_options,
    store_option,
)
from inspect_flow._store.store import (
    FlowStore,
    delete_store,
    resolve_store_path,
    store_exists,
    store_factory,
)
from inspect_flow._types.flow_types import LogFilter
from inspect_flow._types.log_filter import resolve_log_filter
from inspect_flow._util.console import console, flow_print, path, quantity
from inspect_flow._util.logs import copy_all_logs


class ArgumentsHelpCommand(click.Command):
    """Command that displays arguments help section aligned with Options."""

    def __init__(
        self,
        name: str | None,
        *,
        arguments_help: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.arguments_help = arguments_help or {}
        super().__init__(name, **kwargs)

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
    f = store_option(f)
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
            "--recursive/--no-recursive",
            "-r/-R",
            default=True,
            help="Search directories recursively for logs",
            envvar="INSPECT_FLOW_STORE_RECURSIVE",
        )(func)

        return func

    return decorator


def filter_options(f: F) -> F:
    f = click.option(
        "--filter",
        "filter_name",
        type=str,
        multiple=True,
        help="Log filter. Include only logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass).",
        envvar="INSPECT_FLOW_STORE_FILTER",
    )(f)
    f = click.option(
        "--exclude",
        "exclude_name",
        type=str,
        default=None,
        help="Log filter. Include only logs that do NOT pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`.",
        envvar="INSPECT_FLOW_STORE_EXCLUDE",
    )(f)
    return f


def _resolve_cli_filter(
    filter_name: tuple[str, ...], exclude_name: str | None
) -> LogFilter | None:
    if filter_name and exclude_name:
        raise click.UsageError("--filter and --exclude are mutually exclusive.")
    if filter_name:
        return resolve_log_filter(filter_name)
    if exclude_name:
        resolved = resolve_log_filter(exclude_name)
        assert resolved is not None
        return lambda log: not resolved(log)
    return None


class StoreOptionArgs(OutputOptionArgs, total=False):
    store: str | None


def init_store(
    create: bool = False, quiet: bool = False, **kwargs: Unpack[StoreOptionArgs]
) -> FlowStore | None:
    init_output(**kwargs)
    store_location = kwargs.get("store") or "auto"
    flow_store = store_factory(store_location, base_dir=".", create=create, quiet=quiet)
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
    help="Import logs into the store",
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
        file_okay=False,
        dir_okay=True,
        writable=True,
        readable=True,
        resolve_path=False,
    ),
    help="Copy logs from this directory to PATH before importing. Supports both local and S3 paths.",
    envvar="INSPECT_FLOW_STORE_IMPORT_COPY_FROM",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be imported without making changes",
    envvar="INSPECT_FLOW_STORE_IMPORT_DRY_RUN",
)
def store_import(
    path: tuple[str, ...],
    recursive: bool,
    copy_from: str | None,
    dry_run: bool,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    if dry_run:
        flow_print(
            "\n[blue][DRY RUN][/blue] Preview mode - logs will not be imported\n"
        )

    flow_store = init_store(create=True, **kwargs)
    if not flow_store:
        return
    if copy_from:
        if len(path) != 1:
            raise click.UsageError(
                "When using --copy-from, exactly one PATH must be specified"
            )
        copy_all_logs(
            src_dir=copy_from, dest_dir=path[0], dry_run=dry_run, recursive=recursive
        )
    flow_store.import_log_path(
        list(path), recursive=recursive, dry_run=dry_run, verbose=True
    )


@store_command.command(
    "remove",
    help="Remove logs from the store",
    cls=ArgumentsHelpCommand,
    arguments_help={
        "PREFIX...": "One or more prefixes to match against log paths [optional]"
    },
)
@store_options
@filter_options
@click.argument("prefix", nargs=-1, required=False, envvar="INSPECT_FLOW_STORE_PREFIX")
@click.option(
    "--recursive/--no-recursive",
    "-r/-R",
    default=True,
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
def store_remove(
    prefix: tuple[str, ...],
    recursive: bool,
    missing: bool,
    dry_run: bool,
    filter_name: tuple[str, ...],
    exclude_name: str | None,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    if dry_run:
        flow_print("\n[blue][DRY RUN][/blue] Preview mode - logs will not be removed\n")
    if not prefix and not missing:
        raise click.UsageError("Either prefix or --missing must be specified.")
    if prefix and missing:
        raise click.UsageError("Cannot specify both prefix and --missing.")
    log_filter = _resolve_cli_filter(filter_name, exclude_name)
    flow_store = init_store(**kwargs)
    if flow_store:
        flow_store.remove_log_prefix(
            list(prefix),
            missing=missing,
            recursive=recursive,
            dry_run=dry_run,
            verbose=True,
            filter=log_filter,
        )


ListFormat = Literal["flat", "tree"]


def _echo_logs(
    flow_store: FlowStore,
    format: ListFormat = "flat",
    filter: LogFilter | None = None,
) -> None:
    log_files = flow_store.get_logs(filter=filter)
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
    flow_store = init_store(quiet=True, **kwargs)
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
    init_output(**kwargs)
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
@filter_options
@click.option(
    "--format",
    "format",
    type=click.Choice(["flat", "tree"]),
    default="flat",
    help="Output format: tree, flat",
    envvar="INSPECT_FLOW_STORE_LIST_FORMAT",
)
def store_list(
    format: str,
    filter_name: tuple[str, ...],
    exclude_name: str | None,
    **kwargs: Unpack[StoreOptionArgs],
) -> None:
    assert format in ("flat", "tree")
    log_filter = _resolve_cli_filter(filter_name, exclude_name)
    flow_store = init_store(**kwargs)
    if flow_store:
        _echo_logs(flow_store, format=format, filter=log_filter)
