from __future__ import annotations

from inspect_flow._display.display import display
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._runner.logs import find_existing_logs, get_task_ids_to_tasks
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.task_log import TaskLogInfo, create_task_log_display
from inspect_flow._store.store import store_factory
from inspect_flow._types.flow_types import FlowOptions, FlowSpec, FlowStoreConfig
from inspect_flow._util.console import flow_print, path


def check_eval_set(spec: FlowSpec, base_dir: str) -> dict[str, TaskLogInfo]:
    resolved_spec = resolve_spec(spec, base_dir=base_dir)
    options = resolved_spec.options or FlowOptions()

    tasks = instantiate_tasks(resolved_spec, base_dir=base_dir)
    task_id_to_task = get_task_ids_to_tasks(tasks=tasks, spec=resolved_spec)
    store = store_factory(resolved_spec, base_dir=base_dir, create=False)
    store_config = (
        resolved_spec.store
        if isinstance(resolved_spec.store, FlowStoreConfig)
        else None
    )

    if not resolved_spec.log_dir:
        raise ValueError("log_dir must be set before checking the flow spec")
    log_dir = resolved_spec.log_dir

    # Always allow dirty for check — unexpected logs are reported, not an error
    check_options = options.model_copy(update={"log_dir_allow_dirty": True})
    resolved_spec = resolved_spec.model_copy(update={"options": check_options})

    task_log_info = find_existing_logs(
        task_id_to_task,
        resolved_spec,
        store if (store_config is not None and store_config.read) else None,
        dry_run=True,
    )

    display().stop()

    flow_print(create_task_log_display(task_log_info, completed=True))
    flow_print("Log dir:", path(log_dir), soft_wrap=True, crop=False)
    return task_log_info
