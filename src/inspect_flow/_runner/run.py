import time
from datetime import timedelta
from logging import getLogger

import click
import yaml
from inspect_ai import Task, eval_set
from inspect_ai._eval.eval import eval_resolve_tasks
from inspect_ai._eval.evalset import (
    EvalSetArgsInTaskIdentifier,
    epochs_changed,
    task_identifier,
)
from inspect_ai._eval.task.task import resolve_epochs
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import basename, copy_file, file
from inspect_ai.log import EvalLog, read_eval_log
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.util._display import init_display_type
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.instantiate import InstantiatedTask, instantiate_tasks
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._store.deltalake import list_all_eval_logs
from inspect_flow._store.store import FlowStoreInternal, store_factory
from inspect_flow._types.flow_types import (
    FlowOptions,
    FlowSpec,
    FlowTask,
)
from inspect_flow._util.console import flow_print, format_prefix, path, quantity
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.error import FlowHandledError, NoLogsError, set_exception_hook
from inspect_flow._util.list_util import sequence_to_list
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.not_given import default, default_none
from inspect_flow._util.path_util import cwd_relative_path, path_join
from inspect_flow._util.pydantic_util import model_dump
from inspect_flow._util.subprocess_util import signal_ready_and_wait

logger = getLogger(__name__)


def _read_config(config_file: str) -> FlowSpec:
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
        return FlowSpec.model_validate(data, extra="forbid")


def _write_config_file(spec: FlowSpec) -> None:
    filename = f"{spec.log_dir}/flow.yaml"
    yaml = config_to_yaml(spec)
    with file(filename, "w") as f:
        f.write(yaml)


def run_eval_set(
    spec: FlowSpec, base_dir: str, dry_run: bool = False
) -> tuple[bool, list[EvalLog]]:
    resolved_spec = resolve_spec(spec, base_dir=base_dir)
    # 470 - eval_resolve_tasks uses the display, which sets a global that causes it to be ignored when passed to eval_set
    # so we need to initialize the display type here first
    options = resolved_spec.options or FlowOptions()
    if options.display:
        init_display_type(options.display)

    tasks = instantiate_tasks(resolved_spec, base_dir=base_dir)
    task_id_to_task = _get_task_ids_to_tasks(tasks=tasks, spec=resolved_spec)
    store = store_factory(resolved_spec, base_dir=base_dir, create=True)

    if dry_run:
        if store:
            _copy_existing_logs(task_id_to_task, resolved_spec, store, dry_run=True)
        return False, []

    if not resolved_spec.log_dir:
        raise ValueError("log_dir must be set before running the flow spec")

    _write_config_file(resolved_spec)

    num_complete_logs = 0
    if store:
        num_complete_logs = _copy_existing_logs(task_id_to_task, resolved_spec, store)

    if num_complete_logs > 0:
        remaining_tasks = len(tasks) - num_complete_logs
        flow_print(
            f"\nRunning {quantity(remaining_tasks, 'task')} ({quantity(num_complete_logs, 'task')} already complete)"
        )
    else:
        flow_print(f"\nRunning {quantity(len(tasks), 'task')}")
    flow_print("Using log directory:", path(resolved_spec.log_dir), "\n", format="info")

    flow_print(Rule("Running Eval Set"))
    start_time = time.time()
    try:
        result = eval_set(
            tasks=[t.task for t in tasks],
            log_dir=cwd_relative_path(resolved_spec.log_dir),
            retry_attempts=default_none(options.retry_attempts),
            retry_wait=default_none(options.retry_wait),
            retry_connections=default_none(options.retry_connections),
            retry_cleanup=default_none(options.retry_cleanup),
            # model= FlowTask
            # model_base_url= FlowModel
            # model_args= FlowModel
            # model_roles= FlowTask
            # task_args= FlowTask
            sandbox=default_none(options.sandbox),
            sandbox_cleanup=default_none(options.sandbox_cleanup),
            # solver= FlowTask
            tags=sequence_to_list(default_none(options.tags)),
            metadata=default_none(options.metadata),
            trace=default_none(options.trace),
            display=default_none(options.display),
            approval=default_none(options.approval),
            score=default(options.score, True),
            log_level=default_none(options.log_level),
            log_level_transcript=default_none(options.log_level_transcript),
            log_format=default_none(options.log_format),
            limit=default_none(options.limit),
            # sample_id= FlowTask
            sample_shuffle=default_none(options.sample_shuffle),
            # epochs= FlowTask
            fail_on_error=default_none(options.fail_on_error),
            continue_on_fail=default_none(options.continue_on_fail),
            retry_on_error=default(options.retry_on_error, 3),
            debug_errors=default_none(options.debug_errors),
            # message_limit= FlowTask
            # token_limit= FlowTask
            # time_limit= FlowTask
            # working_limit= FlowTask
            max_samples=default_none(options.max_samples),
            max_tasks=default(options.max_tasks, 10),
            max_subprocesses=default_none(options.max_subprocesses),
            max_sandboxes=default_none(options.max_sandboxes),
            log_samples=default_none(options.log_samples),
            log_realtime=default_none(options.log_realtime),
            log_images=default_none(options.log_images),
            log_buffer=default_none(options.log_buffer),
            log_shared=default_none(options.log_shared),
            bundle_dir=default_none(options.bundle_dir),
            bundle_overwrite=default(options.bundle_overwrite, False),
            log_dir_allow_dirty=default_none(options.log_dir_allow_dirty),
            eval_set_id=default_none(options.eval_set_id),
            # kwargs= FlowSpec, FlowTask, and FlowModel allow setting the generate config
        )
    except BaseException as e:
        if isinstance(e, PrerequisiteError):
            _fix_prerequisite_error_message(e)
        if error_string := str(e):
            flow_print(error_string, format="error")
        flow_print(Rule("Eval Set Failed with Exception"))
        if error_string:
            raise FlowHandledError from e
        else:
            raise

    flow_print(Rule("Eval Set Finished"))
    elapsed_time = time.time() - start_time

    _print_result(resolved_spec, result, elapsed_time)

    if store:
        # Now that the logs have been created, need to add the log_dir again to ensure all logs are indexed
        # TODO:ransomr better monitoring of the log directory
        try:
            store.add_run_logs(result[1])
        except NoLogsError as e:
            logger.error(
                f"No logs found in log directory: {resolved_spec.log_dir}. Cannot add to store. {e}"
            )

    if result[0]:
        _print_bundle_url(resolved_spec)

    return result


def _print_result(
    spec: FlowSpec, result: tuple[bool, list[EvalLog]], elapsed_time: float
) -> None:
    success, logs = result
    num_success = len([log for log in logs if log.status == "success"])
    if success and num_success < len(logs):
        logger.error("Some logs failured even though the eval set succeeded.")
    elif not success and num_success == len(logs):
        logger.error("All logs successful even though the eval set failed.")

    if num_success < len(logs):
        summary = format_prefix("warning") + " Completed with errors"
        tasks = f"Tasks: {num_success}/{len(logs)} successful, {len(logs) - num_success} failed"
    else:
        summary = format_prefix("success") + " All tasks completed"
        tasks = f"Tasks: {len(logs)}/{len(logs)} successful"
    assert spec.log_dir
    elapsed = str(timedelta(seconds=int(elapsed_time)))
    flow_print(
        "\n",
        Panel(
            Text.assemble(
                summary,
                "\n\nTotal Time: ",
                elapsed,
                "\n",
                tasks,
                "\nLog Directory: ",
                path(spec.log_dir),
            )
        ),
    )

    if num_success < len(logs):
        flow_print("\nFailed Tasks:")
        for log in logs:
            if log.status == "error":
                flow_print(
                    f"{log.eval.task}: {log.error.message if log.error else 'Unknown error'}",
                    format="error",
                )


def _get_task_ids_to_tasks(
    tasks: list[InstantiatedTask], spec: FlowSpec
) -> dict[str, Task]:
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

    task_ids: dict[str, Task] = dict()
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

        task_ids[task_id] = resolved_task.task
    return task_ids


def _is_complete_log(
    header: EvalLog, task: Task, limit: int | tuple[int, int] | None
) -> bool:
    if not header.results or header.invalidated:
        return False
    epochs = resolve_epochs(task.epochs)
    if epochs_changed(epochs, header.eval.config):
        return False
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

    expected_samples = count * epoch_count
    return header.results.completed_samples == expected_samples


def _copy_existing_logs(
    task_id_to_task: dict[str, Task],
    spec: FlowSpec,
    store: FlowStoreInternal,
    dry_run: bool = False,
) -> int:
    flow_print("Checking for existing logs")
    assert spec.log_dir
    logs = list_all_eval_logs(log_dir=spec.log_dir)
    num_found = 0
    num_complete = 0
    options = spec.options or FlowOptions()
    limit = default_none(options.limit)

    matching_logs = [log for log in logs if log.task_identifier in task_id_to_task]
    if matching_logs:
        num_found += len(matching_logs)
        flow_print(
            f"Found {quantity(len(matching_logs), 'existing log')} in log directory",
            format="info",
        )
        for log in matching_logs:
            task = task_id_to_task[log.task_identifier]
            if _is_complete_log(log.header, task, limit):
                num_complete += 1
            flow_print(
                Text.assemble(log.info.task, " (", path(log.info.name), ")"),
                format="info",
            )
            task_id_to_task.pop(log.task_identifier, None)
        if not task_id_to_task:
            return num_complete

    log_files = store.search_for_logs(set(task_id_to_task.keys()))
    if log_files:
        num_found += len(log_files)
        flow_print(
            f"Found {quantity(len(log_files), 'existing log')}{', copying to log directory' if not dry_run else ''}",
            format="info",
        )
        for task_id, log_file in log_files.items():
            task = task_id_to_task[task_id]
            header = read_eval_log(log_file, header_only=True)
            if _is_complete_log(header, task, limit):
                num_complete += 1
            flow_print(
                Text.assemble(task.name, " (", path(log_file), ")"),
                format="info",
            )
            if not dry_run:
                destination = path_join(spec.log_dir, basename(log_file))
                copy_file(log_file, destination)

    if not num_found:
        flow_print("No existing logs found", format="info")
    return num_complete


def _fix_prerequisite_error_message(e: PrerequisiteError) -> None:
    # Issue #217 - update error message to use 'bundle_overwrite' instead of 'overwrite'
    original_message = str(e.message)
    modified_message = original_message.replace("'overwrite'", "'bundle_overwrite'")
    if original_message != modified_message:
        e.message = modified_message

    original_message = str(e.args[0])
    modified_message = original_message.replace("'overwrite'", "'bundle_overwrite'")
    if original_message != modified_message:
        e.args = (modified_message, *e.args[1:])


def _print_bundle_url(spec: FlowSpec) -> None:
    if spec.options and spec.options.bundle_url_mappings and spec.options.bundle_dir:
        bundle_url = spec.options.bundle_dir
        for local, url in spec.options.bundle_url_mappings.items():
            bundle_url = bundle_url.replace(local, url)
        if bundle_url != spec.options.bundle_dir:
            flow_print(f"Bundle URL: {bundle_url}")


@click.group(invoke_without_command=True)
@click.option(
    "--file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
)
@click.option(
    "--base-dir",
    type=str,
    default="",
    help="Base directory.",
)
@click.option(
    "--log-level",
    type=str,
    default=DEFAULT_LOG_LEVEL,
    help="Log level.",
)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    default=False,
    help="Dry run.",
)
@click.pass_context
def flow_run(
    ctx: click.Context, file: str, base_dir: str, log_level: str, dry_run: bool
) -> None:
    set_exception_hook()

    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        raise NotImplementedError("Run has no subcommands.")

    init_flow_logging(log_level=log_level)
    signal_ready_and_wait()

    cfg = _read_config(file)
    run_eval_set(cfg, base_dir=base_dir, dry_run=dry_run)


if __name__ == "__main__":
    flow_run()
