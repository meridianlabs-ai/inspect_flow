from abc import ABC, abstractmethod
from logging import getLogger
from pathlib import Path
from typing import NamedTuple, Sequence

from inspect_ai._util.file import filesystem
from inspect_ai.log import EvalLog

from inspect_flow._display.display import display
from inspect_flow._types.flow_types import (
    FlowSpec,
    FlowStoreConfig,
    LogFilter,
    NotGiven,
)
from inspect_flow._types.log_filter import resolve_log_filter
from inspect_flow._util.console import path
from inspect_flow._util.data import user_data_dir
from inspect_flow._util.logs import num_valid_samples
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(__name__)


class FlowStore(ABC):
    """Interface for flow store implementations."""

    @property
    @abstractmethod
    def store_path(self) -> str:
        """The path to the store directory."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """The store version."""
        ...

    @abstractmethod
    def import_log_path(
        self,
        log_path: str | Sequence[str],
        recursive: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> None:
        """Import a log file(s) or directory(ies) into the store.

        Args:
            log_path: Path or paths to log files or directories containing log files.
            recursive: Whether to search directories recursively.
            dry_run: Preview what would be imported without making changes
            verbose: Print paths of files being added
        """
        pass

    @abstractmethod
    def get_logs(self, filter: LogFilter | None = None) -> set[str]:
        """Get all log file paths in the store.

        Args:
            filter: Optional filter to apply to log headers. Only logs passing
                the filter are included. It is an error to specify both a
                per-call filter and a store-level filter.

        Returns:
            Set of log file paths in the store.
        """
        pass

    @abstractmethod
    def remove_log_prefix(
        self,
        prefix: str | Sequence[str],
        missing: bool = False,
        recursive: bool = False,
        dry_run: bool = False,
        verbose: bool = True,
        filter: LogFilter | None = None,
    ) -> None:
        """Remove logs matching the given prefixes.

        Args:
            prefix: One or more prefixes to match against log paths.
            missing: Whether to remove log paths that are missing from the file system.
            recursive: Whether to remove log files recursively.
            dry_run: Preview what would be removed without making changes
            verbose: Print paths of files being removed
            filter: Optional filter to narrow which matched logs are removed.
                Each candidate log's header is read and only those passing
                the filter are removed.
        """
        pass


class StoreLogMatch(NamedTuple):
    log_file: str
    duplicate_logs: list[str]


class FlowStoreInternal(FlowStore):
    """Internal interface for flow store implementations."""

    @abstractmethod
    def search_for_logs(self, task_ids: set[str]) -> dict[str, StoreLogMatch]:
        pass

    def add_run_logs(self, eval_logs: list[EvalLog]) -> None:
        pass


def is_better_log(candidate: EvalLog, best: EvalLog | None) -> bool:
    """Compare two logs and determine if candidate is better than best.

    Args:
        candidate: The candidate log to evaluate.
        best: The current best log, or None if no best exists.

    Returns:
        True if candidate should replace best, False otherwise.
    """
    if best is None:
        return True
    candidate_samples = num_valid_samples(candidate)
    best_samples = num_valid_samples(best)
    if best_samples > candidate_samples:
        return False
    if candidate_samples > best_samples:
        return True
    # If completed samples are equal, take the more recently completed one
    return candidate.stats.completed_at > best.stats.completed_at


def _get_default_store_dir() -> Path:
    return user_data_dir()


def _store_mode_label(store_config: FlowStoreConfig | None) -> str:
    read = store_config.read if store_config is not None else False
    write = store_config.write if store_config is not None else True
    if read and write:
        return " (read-write)"
    if read:
        return " (read only)"
    return " (write only)"


def store_factory(
    spec_or_store: FlowSpec | str,
    base_dir: str,
    create: bool = False,
    quiet: bool = False,
) -> FlowStoreInternal | None:
    store = spec_or_store if isinstance(spec_or_store, str) else spec_or_store.store
    if isinstance(store, NotGiven):
        store = "auto"

    log_filter: LogFilter | None = None
    store_config: FlowStoreConfig | None = None
    if isinstance(store, FlowStoreConfig):
        store_config = store
        log_filter = resolve_log_filter(store.filter, base_dir=base_dir)
        store = store.path

    if store is None or store.lower() == "none":
        return None
    if store.lower() == "auto":
        store = str(_get_default_store_dir())

    if store_config is not None and not store_config.read and not store_config.write:
        return None

    # Import here to avoid circular imports
    from inspect_flow._store.deltalake import DeltaLakeStore

    store_path = absolute_path_relative_to(store, base_dir=base_dir)
    dl_store = DeltaLakeStore(store_path, create=create, log_filter=log_filter)
    if dl_store.exists and not quiet:
        display().print(
            f"Using store{_store_mode_label(store_config)}:",
            path(store_path),
            action_key="logs",
        )
    return dl_store if dl_store.exists else None


def resolve_store_path(store: str | None, base_dir: str = ".") -> str:
    location = store or "auto"
    if location.lower() == "auto":
        location = str(_get_default_store_dir())
    return absolute_path_relative_to(location, base_dir=base_dir)


def _flow_store_path(store_path: str) -> str:
    fs = filesystem(store_path)
    return store_path.rstrip(fs.sep) + fs.sep + "flow_store"


def store_exists(store_path: str) -> bool:
    fs = filesystem(store_path)
    return fs.exists(_flow_store_path(store_path))


def delete_store(store_path: str) -> None:
    """Delete a flow store.

    Args:
        store_path: Path to the store directory.
    """
    flow_path = _flow_store_path(store_path)
    fs = filesystem(flow_path)
    fs.rm(flow_path, recursive=True)
