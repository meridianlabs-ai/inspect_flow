from __future__ import annotations

from logging import getLogger

from inspect_ai import Epochs, Task
from inspect_ai._eval.eval import eval_resolve_tasks
from inspect_ai._eval.evalset import (
    EvalSetArgsInTaskIdentifier,
    Log,
    list_all_eval_logs,
    task_identifier,
)
from inspect_ai._eval.task.task import resolve_epochs
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import basename, copy_file
from inspect_ai.log import EvalConfig, EvalLog, read_eval_log
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.scorer._reducer.registry import reducer_log_name

from inspect_flow._display.path_progress import ReadLogsProgress
from inspect_flow._display.run_action import RunAction
from inspect_flow._runner.instantiate import InstantiatedTask
from inspect_flow._runner.task_log import TaskLogInfo
from inspect_flow._store.store import FlowStoreInternal
from inspect_flow._types.flow_types import (
    FlowOptions,
    FlowSpec,
    FlowTask,
)
from inspect_flow._util.console import quantity
from inspect_flow._util.not_given import default_none
from inspect_flow._util.path_util import path_join, path_str
from inspect_flow._util.pydantic_util import model_dump

logger = getLogger(__name__)


def get_task_ids_to_tasks(
    tasks: list[InstantiatedTask], spec: FlowSpec
) -> dict[str, InstantiatedTask]:
    if not tasks:
        return dict()

    options = spec.options or FlowOptions()

    resolved_tasks, _ = eval_resolve_tasks(
        tasks=[t.task for t in tasks],
        task_args=dict(),
        models=[get_model("none")],
        model_roles=None,
        config=GenerateConfig(),
        approval=default_none(options.approval),
        sandbox=default_none(options.sandbox),
        sample_shuffle=default_none(options.sample_shuffle),
    )

    task_ids: dict[str, InstantiatedTask] = dict()
    for i, resolved_task in enumerate(resolved_tasks):
        task_id = task_identifier(
            task=resolved_task,
            eval_set_args=EvalSetArgsInTaskIdentifier(config=GenerateConfig()),
        )
        if task_id in task_ids:
            flow_task = tasks[i].flow_task
            if isinstance(flow_task, FlowTask):
                task_json = model_dump(flow_task)
                raise ValueError(f"Duplicate task found: {task_json}")
            else:
                raise ValueError(f"Duplicate task found: {resolved_task}")

        task_ids[task_id] = tasks[i]
    return task_ids


def _num_samples(task: Task, limit: int | tuple[int, int] | None) -> int:
    epochs = resolve_epochs(task.epochs)
    epoch_count = epochs.epochs if epochs else 1
    count = len(task.dataset)
    if isinstance(limit, tuple):
        start, stop = limit
        if start >= count:
            count = 0
        else:
            count = min(stop, count) - start
    elif isinstance(limit, int):
        count = min(limit, count)
    return count * epoch_count


def _epochs_reducer_changed(epochs: Epochs | None, config: EvalConfig) -> bool:
    # user didn't say anything about epochs on subsequent call (not changed)
    if epochs is None:
        return False
    default_epoch_reducer = ["mean"]
    if epochs.reducer is None and config.epochs_reducer == default_epoch_reducer:
        return False
    return [reducer_log_name(r) for r in (epochs.reducer or [])] != [
        r for r in (config.epochs_reducer or [])
    ]


def num_log_samples(
    header: EvalLog, log_info: TaskLogInfo, limit: int | tuple[int, int] | None
) -> int:
    if not header.results or header.invalidated:
        return 0
    task = log_info.task
    epochs = resolve_epochs(
        Epochs(task.epochs, reducer=task.epochs_reducer)
        if task.epochs and task.epochs_reducer
        else task.epochs
    )
    if _epochs_reducer_changed(epochs, header.eval.config):
        return 0
    epoch_count = epochs.epochs if epochs else 1
    log_epoch_count = header.eval.config.epochs or 1
    if log_epoch_count <= epoch_count:
        return header.results.completed_samples
    else:
        # Log has more epochs than the current task - unclear how many samples can be reused.
        # Assume that samples are evenly distributed across epochs.
        return int(header.results.completed_samples * epoch_count / log_epoch_count)


def find_existing_logs(
    task_id_to_task: dict[str, InstantiatedTask],
    spec: FlowSpec,
    store: FlowStoreInternal | None,
    dry_run: bool = False,
) -> dict[str, TaskLogInfo]:
    with RunAction("logs") as action:
        assert spec.log_dir
        with ReadLogsProgress(action=action) as progress:
            logs = list_all_eval_logs(log_dir=spec.log_dir, progress=progress)
        num_found = 0
        options = spec.options or FlowOptions()
        limit = default_none(options.limit)

        logs_by_task: dict[str, list[Log]] = {}
        for log in logs:
            if log.task_identifier in task_id_to_task:
                logs_by_task.setdefault(log.task_identifier, []).append(log)
            elif not options.log_dir_allow_dirty:
                action.update(
                    status="error",
                    info=[
                        "log_dir contains unexpected log. Use --log-dir-allow-dirty to allow."
                    ],
                )
                raise PrerequisiteError(
                    f"[bold]ERROR[/bold]: Existing log file '{path_str(log.info.name)}' in log_dir is not "
                    + "associated with a task. You can use the `--log-dir-allow-dirty` option to allow "
                    + "logs from other evals to be present in the log directory."
                )

        result = {
            id: TaskLogInfo(
                task=it.task,
                flow_task=it.flow_task,
                task_samples=_num_samples(it.task, limit),
            )
            for id, it in task_id_to_task.items()
        }

        num_found = 0
        for id, log_info in result.items():
            for log in logs_by_task.get(id, []):
                log_samples = num_log_samples(log.header, log_info, limit)
                if log_samples >= log_info.log_samples:
                    log_info.log_samples = log_samples
                    log_info.log_file = log.info.name
                    if task_id_to_task.pop(id, None):
                        num_found += 1

        if num_found:
            action.update(
                info=f"Found {quantity(num_found, 'existing log')} in log directory"
            )
        else:
            action.update(info="No existing logs found in log directory")

        if not task_id_to_task or not store:
            return result

        log_files = store.search_for_logs(set(task_id_to_task.keys()))
        if log_files:
            if num_found:
                action.update(
                    info=f"Found {quantity(num_found, 'existing log')} in log directory. Copying {quantity(len(log_files), 'existing log')}, to log directory"
                )
            else:
                action.update(
                    info=f"Copying {quantity(len(log_files), 'existing log')} to log dir"
                )
            num_found += len(log_files)
            for task_id, log_file in log_files.items():
                log_info = result[task_id]
                header = read_eval_log(log_file, header_only=True)
                log_info.log_file = log_file
                log_info.log_samples = num_log_samples(header, log_info, limit)
                if not dry_run:
                    destination = path_join(spec.log_dir, basename(log_file))
                    copy_file(log_file, destination)

        if not num_found:
            action.update(info="No existing logs found", status="success")
    return result
