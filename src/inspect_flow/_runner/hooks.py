from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from logging import getLogger

from inspect_ai.hooks import Hooks, TaskStart
from inspect_ai.log import list_eval_logs, read_eval_log

from inspect_flow._store.store import FlowStoreInternal

logger = getLogger(__name__)

_store: FlowStoreInternal | None = None
_log_dir: str | None = None


# @hooks(
#     name="flow_store",
#     description="Adds eval logs to inspect flow store on task start",
# )
class FlowStoreHook(Hooks):
    def enabled(self) -> bool:
        return _store is not None and _log_dir is not None

    async def on_task_start(self, data: TaskStart) -> None:
        assert _store is not None and _log_dir is not None
        # list_eval_logs returns files sorted by mtime descending,
        # so the just-created log file should be near the top
        log_files = list_eval_logs(_log_dir, recursive=False)
        for log_info in log_files:
            header = read_eval_log(log_info.name, header_only=True)
            if header.eval.eval_id == data.eval_id:
                _store.add_run_logs([header])
                return
        logger.warning(
            f"Could not find log file for task {data.spec.task} "
            f"(eval_id={data.eval_id})"
        )


@contextmanager
def flow_store_hook(store: FlowStoreInternal, log_dir: str) -> Iterator[None]:
    global _store, _log_dir
    _store = store
    _log_dir = log_dir
    try:
        yield
    finally:
        _store = None
        _log_dir = None
