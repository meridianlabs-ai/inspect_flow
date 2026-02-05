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

    @property
    @abstractmethod
    def store_path(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

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
        verbose: bool = False,
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
    return Path(platformdirs.user_data_dir(PKG_NAME))


def store_factory(
    spec_or_store: FlowSpec | str, base_dir: str, create: bool = False
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
    store = DeltaLakeStore(store_path, create=create)
    return store if store.exists else None
