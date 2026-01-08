import click

from inspect_flow._store.store import FlowStore, store_factory


def _get_store(store_path: str | None) -> FlowStore:
    """Get a FlowStore instance from the given path or default location."""
    store_location = store_path or "auto"
    flow_store = store_factory(store_location, base_dir=".")
    assert flow_store is not None
    return flow_store


@click.group("store", help="Manage the flow store")
def store_command() -> None:
    """CLI command group for flow store operations."""
    pass


@store_command.command("add", help="Add log directories to the store")
@click.argument("log_dirs", nargs=-1, required=True)
@click.option(
    "--store",
    "-s",
    type=str,
    default=None,
    help="Path to the store directory. Defaults to the default store location.",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    default=False,
    help="Recursively search for log directories.",
)
def store_add(log_dirs: tuple[str, ...], store: str | None, recursive: bool) -> None:
    """Add log directories to the flow store."""
    flow_store = _get_store(store)
    flow_store.add_log_dir(list(log_dirs), recursive=recursive)
    click.echo(
        f"Added {len(log_dirs)} log director{'y' if len(log_dirs) == 1 else 'ies'} to the store."
    )


@store_command.command("remove", help="Remove log directories from the store")
@click.argument("log_dirs", nargs=-1, required=True)
@click.option(
    "--store",
    "-s",
    type=str,
    default=None,
    help="Path to the store directory. Defaults to the default store location.",
)
def store_remove(log_dirs: tuple[str, ...], store: str | None) -> None:
    """Remove log directories from the flow store."""
    flow_store = _get_store(store)
    flow_store.remove_log_dir(list(log_dirs))
    click.echo(
        f"Removed {len(log_dirs)} log director{'y' if len(log_dirs) == 1 else 'ies'} from the store."
    )


@store_command.command("list", help="List log directories in the store")
@click.option(
    "--store",
    "-s",
    type=str,
    default=None,
    help="Path to the store directory. Defaults to the default store location.",
)
def store_list(store: str | None) -> None:
    """List all log directories in the flow store."""
    flow_store = _get_store(store)
    log_dirs = flow_store.get_log_dirs()
    if log_dirs:
        for log_dir in sorted(log_dirs):
            click.echo(log_dir)
    else:
        click.echo("No log directories in the store.")


@store_command.command(
    "refresh", help="Refresh the store to reflect the current file system state"
)
@click.option(
    "--store",
    "-s",
    type=str,
    default=None,
    help="Path to the store directory. Defaults to the default store location.",
)
def store_refresh(store: str | None) -> None:
    """Refresh the flow store to reflect the current state of the file system."""
    flow_store = _get_store(store)
    flow_store.refresh()
    click.echo("Store refreshed.")
