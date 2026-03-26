from __future__ import annotations

from inspect_flow._display.run_action import RunAction
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._runner.logs import find_existing_logs, get_task_ids_to_tasks
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.task_log import create_task_log_display
from inspect_flow._store.store import store_factory
from inspect_flow._types.flow_types import FlowSpec, FlowStoreConfig
from inspect_flow._util.console import path


def check_eval_set(spec: FlowSpec, base_dir: str) -> None:
    resolved_spec = resolve_spec(spec, base_dir=base_dir)

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

    logs_result = find_existing_logs(
        task_id_to_task,
        resolved_spec,
        store if (store_config is not None and store_config.read) else None,
        mode="check",
    )

    with RunAction("logs") as action:
        action.print(create_task_log_display(logs_result.task_log_info, mode="check"))
        if logs_result.unexpected_logs:
            action.print("")
            action.print("Unexpected logs:", format="warning")
            for log_name in logs_result.unexpected_logs:
                action.print(path(log_name))
        action.print("Log dir:", path(log_dir), copyable=True)
        action.print("")
