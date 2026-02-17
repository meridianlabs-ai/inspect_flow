from __future__ import annotations

import time
from datetime import timedelta
from logging import getLogger

import click
import yaml
from inspect_ai import Epochs, Task, eval_set
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
from inspect_ai.util._display import init_display_type
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from inspect_flow._config.write import write_config_file
from inspect_flow._display.display import (
    DisplayAction,
    DisplayType,
    create_display,
    display,
    get_display_type,
    set_display_type,
)
from inspect_flow._display.path_progress import ReadLogsProgress
from inspect_flow._display.run_action import RunAction
from inspect_flow._runner.instantiate import InstantiatedTask, instantiate_tasks
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.task_log import TaskLogInfo, create_task_log_display
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
from inspect_flow._util.path_util import cwd_relative_path, path_join, path_str
from inspect_flow._util.pydantic_util import model_dump
from inspect_flow._util.subprocess_util import signal_ready_and_wait

logger = getLogger(__name__)

VENV_ACTIONS = {
    "instantiate": DisplayAction(description="Instantiate tasks"),
    "logs": DisplayAction(description="Check for existing logs"),
    "evalset": DisplayAction(description="Run evalset"),
}


def _read_config(config_file: str) -> FlowSpec:
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
        return FlowSpec.model_validate(data, extra="forbid")


def _option_string(options: FlowOptions) -> str | None:
    if not options.model_fields_set:
        return None
    return ", ".join(f"{k}={getattr(options, k)!r}" for k in options.model_fields_set)


def run_eval_set(
    spec: FlowSpec, base_dir: str, dry_run: bool = False
) -> tuple[bool, list[EvalLog]]:
    resolved_spec = resolve_spec(spec, base_dir=base_dir)
    # 470 - eval_resolve_tasks uses the display, which sets a global that causes it to be ignored when passed to eval_set
    # so we need to initialize the display type here first
    options = resolved_spec.options or FlowOptions()
    display_type = options.display or get_display_type()
    init_display_type(display_type)

    tasks = instantiate_tasks(resolved_spec, base_dir=base_dir)
    task_id_to_task = _get_task_ids_to_tasks(tasks=tasks, spec=resolved_spec)
    store = store_factory(resolved_spec, base_dir=base_dir, create=True)

    if not resolved_spec.log_dir:
        raise ValueError("log_dir must be set before running the flow spec")

    if not dry_run:
        write_config_file(resolved_spec)

    task_log_info = _find_existing_logs(
        task_id_to_task, resolved_spec, store, dry_run=dry_run
    )

    with RunAction("evalset") as action:
        action.print(create_task_log_display(task_log_info, completed=False))
        if option_str := _option_string(options):
            action.print("\nOptions:", option_str)
        action.print("\nLog dir:", path(resolved_spec.log_dir))

    if dry_run:
        return False, []

    title = display().get_title()
    display().stop()

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
            display=default_none(display_type),
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

    elapsed_time = time.time() - start_time

    _print_result(resolved_spec, result, elapsed_time, task_log_info, title)

    if store:
        # Now that the logs have been created, need to add the log_dir again to ensure all logs are indexed
        # TODO:ransomr better monitoring of the log directory
        try:
            store.add_run_logs(result[1])
        except NoLogsError as e:
            logger.error(
                f"No logs found in log directory: {resolved_spec.log_dir}. Cannot add to store. {e}"
            )

    return result


def _print_result(
    spec: FlowSpec,
    result: tuple[bool, list[EvalLog]],
    elapsed_time: float,
    task_log_info: dict[str, TaskLogInfo],
    title: list[str | Text] | None,
) -> None:
    success, logs = result
    num_success = len([log for log in logs if log.status == "success"])
    if success and num_success < len(logs):
        logger.error("Some logs failured even though the eval set succeeded.")
    elif not success and num_success == len(logs):
        logger.error("All logs successful even though the eval set failed.")

    if num_success < len(logs):
        summary = format_prefix("warning") + " Completed with errors"
    else:
        summary = format_prefix("success") + " All tasks completed"
    assert spec.log_dir
    elapsed = str(timedelta(seconds=int(elapsed_time)))

    options = spec.options or FlowOptions()
    for log in logs:
        id = task_identifier(log, None)
        info = task_log_info.get(id)
        if not info:
            logger.error(f"Log returned that does not match any task: {log.location}")
        else:
            info.log_samples = _num_log_samples(log, info, default_none(options.limit))
            info.log_file = log.location

    task_log = create_task_log_display(task_log_info, completed=True)

    if title:
        spaced = [x for p in title for x in (" ", p)][1:]
        title_text = Text.assemble("[", *spaced, "]", end="")
    else:
        title_text = None

    output = [
        Text.assemble(
            summary, "\n", format_prefix("info"), " Total Time: ", elapsed, "\n"
        ),
        task_log,
        Text.assemble("\nLog dir: ", path(spec.log_dir)),
    ]
    if success:
        bundle_url_output = _bundle_url_output(spec)
        if bundle_url_output:
            output.append(Text.assemble("\n", bundle_url_output))

    flow_print(
        Panel(
            Group(*output),
            title=title_text,
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
    return [r.__name__ for r in (epochs.reducer or [])] != [
        r for r in (config.epochs_reducer or [])
    ]


def _num_log_samples(
    header: EvalLog, log_info: TaskLogInfo, limit: int | tuple[int, int] | None
) -> int:
    if not header.results or header.invalidated:
        return 0
    epochs = resolve_epochs(log_info.task.epochs)
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


def _find_existing_logs(
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
                log_samples = _num_log_samples(log.header, log_info, limit)
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
                log_info.log_samples = _num_log_samples(header, log_info, limit)
                if not dry_run:
                    destination = path_join(spec.log_dir, basename(log_file))
                    copy_file(log_file, destination)

        if not num_found:
            action.update(info="No existing logs found", status="success")
    return result


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


def _bundle_url_output(spec: FlowSpec) -> Text | None:
    if spec.options and spec.options.bundle_dir:
        bundle_url = spec.options.bundle_dir
        if spec.options.bundle_url_mappings:
            for local, url in spec.options.bundle_url_mappings.items():
                bundle_url = bundle_url.replace(local, url)
        if bundle_url != spec.options.bundle_dir:
            return Text.assemble("Bundle URL: ", path(bundle_url))
        else:
            return Text.assemble("Bundle dir: ", path(bundle_url))
    return None


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
@click.option(
    "--display",
    "display_type",
    type=click.Choice(["full", "rich", "plain"]),
    default="plain",
    help="Display type.",
)
@click.pass_context
def flow_run(
    ctx: click.Context,
    file: str,
    base_dir: str,
    log_level: str,
    dry_run: bool,
    display_type: DisplayType,
) -> None:
    set_exception_hook()

    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        raise NotImplementedError("Run has no subcommands.")

    init_flow_logging(log_level=log_level)
    signal_ready_and_wait()

    set_display_type(display_type)
    cfg = _read_config(file)
    with create_display(dry_run=dry_run, actions=VENV_ACTIONS) as display:
        display.set_title("VENV Flow Spec:", path(file))
        run_eval_set(cfg, base_dir=base_dir, dry_run=dry_run)


if __name__ == "__main__":
    flow_run()
