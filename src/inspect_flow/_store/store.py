from abc import ABC, abstractmethod
from logging import getLogger
from pathlib import Path
from typing import Sequence

import platformdirs
from inspect_ai.log import EvalLog

from inspect_flow._types.flow_types import FlowSpec, NotGiven
from inspect_flow._util.constants import PKG_NAME
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(__name__)


class FlowStore(ABC):
    """Interface for flow store implementations."""

    @abstractmethod
    def add_log_dir(
        self, log_dir: str | Sequence[str], recursive: bool = False
    ) -> None:
        """Add a directory of log files.

        Args:
            log_dir: Path or paths to directories containing log files.
            recursive: Whether to search directories recursively.
        """
        pass

    @abstractmethod
    def get_log_dirs(self) -> set[str]:
        """Get all registered log directories.

        Returns:
            Set of log directory paths that have been added to the store.
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
    def remove_log_dir(self, log_dir: str | Sequence[str]) -> None:
        """Remove a directory of log files.

        Args:
            log_dir: Path or paths to directories containing log files.
        """
        pass

    @abstractmethod
    def refresh(self) -> None:
        """Refresh the store to reflect the current state of the file system."""
        pass


class FlowStoreInternal(FlowStore):
    """Internal interface for flow store implementations."""

    @abstractmethod
    def search_for_logs(self, task_ids: set[str]) -> list[str]:
        """Search for logs matching the given task IDs.

        Args:
            task_ids: Set of task identifiers to search for.

        Returns:
            List of log file paths for the best log of each task.
        """
        pass


def is_better_log(candidate: EvalLog, best: EvalLog | None) -> bool:
    """Compare two logs and determine if candidate is better than best.

    Args:
        candidate: The candidate log to evaluate.
        best: The current best log, or None if no best exists.

    Returns:
        True if candidate should replace best, False otherwise.
    """
    if not candidate.results or candidate.invalidated:
        return False
    if best is None:
        return True
    # Compare completed samples
    assert best.results
    if candidate.results.completed_samples > best.results.completed_samples:
        return True
    if candidate.results.completed_samples < best.results.completed_samples:
        return False
    # If completed samples are equal, take the more recently completed one
    return candidate.stats.completed_at > best.stats.completed_at


def _get_default_store_dir() -> Path:
    return Path(platformdirs.user_data_dir(PKG_NAME)) / "store"


def store_factory(
    spec_or_store: FlowSpec | str, base_dir: str
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
    return DeltaLakeStore(store_path)
