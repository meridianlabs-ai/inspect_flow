from abc import ABC, abstractmethod
from logging import getLogger
from pathlib import Path

import platformdirs
from inspect_ai.log import EvalLog

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.constants import PKG_NAME
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(__name__)


class FlowStore(ABC):
    """Interface for flow database implementations."""

    @abstractmethod
    def add_log_dir(self, log_dir: str) -> None:
        pass

    @abstractmethod
    def get_log_dirs(self) -> set[str]:
        pass


class FlowStoreInternal(FlowStore):
    """Internal interface for flow database implementations."""

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
    if store is None:
        return None
    if not store:
        store = "auto"
    if store == "auto":
        store = str(_get_default_store_dir())

    # Import here to avoid circular imports
    from inspect_flow._store.deltalake import DeltaLakeStore

    database_path = Path(absolute_path_relative_to(store, base_dir=base_dir))
    return DeltaLakeStore(database_path)
