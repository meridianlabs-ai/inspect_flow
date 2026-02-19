from __future__ import annotations

import time
from datetime import timedelta
from logging import getLogger

from inspect_ai import eval_set
from inspect_ai._eval.evalset import task_identifier
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.log import EvalLog
from inspect_ai.util._display import init_display_type
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from inspect_flow._config.write import write_config_file
from inspect_flow._display.display import display, get_display_type
from inspect_flow._display.run_action import RunAction
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._runner.logs import (
    find_existing_logs,
    get_task_ids_to_tasks,
    num_log_samples,
)
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.task_log import TaskLogInfo, create_task_log_display
from inspect_flow._store.store import store_factory
from inspect_flow._types.flow_types import (
    FlowOptions,
    FlowSpec,
)
from inspect_flow._util.console import flow_print, format_prefix, path
from inspect_flow._util.error import FlowHandledError, NoLogsError
from inspect_flow._util.list_util import sequence_to_list
from inspect_flow._util.not_given import default, default_none
from inspect_flow._util.path_util import cwd_relative_path

logger = getLogger(__name__)


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
    task_id_to_task = get_task_ids_to_tasks(tasks=tasks, spec=resolved_spec)
    store = store_factory(resolved_spec, base_dir=base_dir, create=True)

    if not resolved_spec.log_dir:
        raise ValueError("log_dir must be set before running the flow spec")

    if not dry_run:
        write_config_file(resolved_spec)

    task_log_info = find_existing_logs(
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
        logger.error("Some logs failed even though the eval set succeeded.")
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
            info.log_samples = num_log_samples(log, info, default_none(options.limit))
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
