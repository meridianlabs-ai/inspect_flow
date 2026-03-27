from __future__ import annotations

from inspect_flow._api.api import CheckResult, CheckTask
from inspect_flow._display.run_action import RunAction
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._runner.logs import (
    FindLogsResult,
    find_existing_logs,
    get_task_ids_to_tasks,
)
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.task_log import create_task_log_display
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.console import path


def _to_check_result(logs_result: FindLogsResult) -> CheckResult:
    tasks = []
    for info in logs_result.task_log_info.values():
        assert info.flow_task is not None
        tasks.append(
            CheckTask(
                name=info.task.name,
                task=info.flow_task,
                log_file=info.log_file,
                samples=info.log_samples,
                total_samples=info.task_samples,
            )
        )
    return CheckResult(tasks=tasks, unrecognized=logs_result.unexpected_logs)


def check_eval_set(spec: FlowSpec, base_dir: str) -> CheckResult:
    resolved_spec = resolve_spec(spec, base_dir=base_dir)

    tasks = instantiate_tasks(resolved_spec, base_dir=base_dir)
    task_id_to_task = get_task_ids_to_tasks(tasks=tasks, spec=resolved_spec)

    if not resolved_spec.log_dir:
        raise ValueError("log_dir must be set before checking the flow spec")
    log_dir = resolved_spec.log_dir

    logs_result = find_existing_logs(
        task_id_to_task,
        resolved_spec,
        store=None,  # Check checks if the logs are in the log_dir and does not use the store
        mode="check",
    )

    with RunAction("logs") as action:
        action.print(create_task_log_display(logs_result.task_log_info, mode="check"))
        if logs_result.unexpected_logs:
            action.print("")
            action.print("Unexpected logs:", format="warning")
            for log_name in logs_result.unexpected_logs:
                action.print(path(log_name))
        if logs_result.duplicate_logs:
            action.print("")
            action.print("Duplicate logs:", format="info")
            for log_name in logs_result.duplicate_logs:
                action.print(path(log_name))
        action.print("Log dir:", path(log_dir), copyable=True)
        action.print("")

    return _to_check_result(logs_result)
