from abc import ABC, abstractmethod
from logging import getLogger
from pathlib import Path
from typing import Sequence

from inspect_ai._util.file import filesystem
from inspect_ai.log import EvalLog

from inspect_flow._types.flow_types import FlowSpec, NotGiven
from inspect_flow._util.data import user_data_dir
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
    def get_logs(self) -> set[str]:
        """Get all log file paths in the store.

        Returns:
            List of all log file paths in the store.
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
    ) -> None:
        """Remove logs matching the given prefixes.

        Args:
            prefix: One or more prefixes to match against log paths.
            missing: Whether to remove log paths that are missing from the file system.
            recursive: Whether to remove log files recursively.
            dry_run: Preview what would be removed without making changes
            verbose: Print paths of files being removed
        """
        pass


class FlowStoreInternal(FlowStore):
    """Internal interface for flow store implementations."""

    @abstractmethod
    def search_for_logs(self, task_ids: set[str]) -> dict[str, str]:
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
    if not candidate.results or candidate.invalidated:
        return False
    if not best.results or best.invalidated:
        return True
    # Compare completed samples
    if candidate.results.completed_samples > best.results.completed_samples:
        return True
    if candidate.results.completed_samples < best.results.completed_samples:
        return False
    # If completed samples are equal, take the more recently completed one
    return candidate.stats.completed_at > best.stats.completed_at


def _get_default_store_dir() -> Path:
    return user_data_dir()


def store_factory(
    spec_or_store: FlowSpec | str,
    base_dir: str,
    create: bool = False,
    quiet: bool = False,
) -> FlowStoreInternal | None:
    store = spec_or_store if isinstance(spec_or_store, str) else spec_or_store.store
    if isinstance(store, NotGiven):
        store = "auto"
    elif store is None or store.lower() == "none":
        return None
    if store.lower() == "auto":
        store = str(_get_default_store_dir())

    # Import here to avoid circular imports
    from inspect_flow._store.deltalake import DeltaLakeStore

    store_path = absolute_path_relative_to(store, base_dir=base_dir)
    store = DeltaLakeStore(store_path, create=create, quiet=quiet)
    return store if store.exists else None


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
    path = _flow_store_path(store_path)
    fs = filesystem(path)
    fs.rm(path, recursive=True)
