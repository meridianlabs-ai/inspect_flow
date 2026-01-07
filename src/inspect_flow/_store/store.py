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
    """Abstract interface for flow database implementations."""

    @abstractmethod
    def add_log_dir(self, log_dir: str) -> None:
        """Add a log directory to the database."""
        pass

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


def create_store(spec: FlowSpec, base_dir: str) -> FlowStore | None:
    """Create a FlowStore instance based on the spec configuration.

    Args:
        spec: The flow specification containing store configuration.
        base_dir: Base directory for resolving relative paths.

    Returns:
        A FlowStore instance, or None if no store is configured.
    """
    if spec.store is None:
        return None
    if not spec.store:
        spec.store = "auto"
    if spec.store == "auto":
        spec.store = str(_get_default_store_dir())

    # Import here to avoid circular imports
    from inspect_flow._store.deltalake import DeltaLakeStore

    database_path = Path(absolute_path_relative_to(spec.store, base_dir=base_dir))
    return DeltaLakeStore(database_path)
