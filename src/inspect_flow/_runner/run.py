from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from importlib.metadata import PackageNotFoundError, requires, version
from logging import getLogger
from typing import NamedTuple

import click
from inspect_ai._display.textual.app import set_flow_content
from inspect_ai._eval.evalset import list_all_eval_logs, task_identifier
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.log import EvalLog
from inspect_ai.util import DisplayType
from inspect_ai.util._display import init_display_type
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from inspect_flow._config.write import write_config_file
from inspect_flow._display.display import display, get_display_type
from inspect_flow._display.path_progress import ReadLogsProgress
from inspect_flow._display.run_action import RunAction
from inspect_flow._runner.eval_set import eval_set_call, load_preload_files
from inspect_flow._runner.instantiate import InstantiatedTask, instantiate_tasks
from inspect_flow._runner.logs import (
    FindLogsResult,
    find_existing_logs,
    get_task_ids_to_tasks,
    num_log_samples,
)
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._runner.task_log import TaskLogInfo, create_task_log_display
from inspect_flow._store.store import FlowStoreInternal, store_factory
from inspect_flow._types.after_instantiate import run_after_instantiate_hooks
from inspect_flow._types.flow_types import (
    FlowOptions,
    FlowSpec,
    FlowStoreConfig,
)
from inspect_flow._util.console import flow_print, format_prefix, path
from inspect_flow._util.error import FlowHandledError, NoLogsError
from inspect_flow._util.logging import get_last_log_level, update_log_level
from inspect_flow._util.not_given import default_none
from inspect_flow._util.path_util import apply_bundle_url_mappings

logger = getLogger(__name__)


class LaunchResult(NamedTuple):
    success: bool
    logs: list[EvalLog]


def _option_string(options: FlowOptions) -> str | None:
    if not options.model_fields_set:
        return None
    return ", ".join(f"{k}={getattr(options, k)!r}" for k in options.model_fields_set)


@dataclass
class _RunContext:
    spec: FlowSpec
    options: FlowOptions
    display_type: DisplayType
    log_level: str
    tasks: list[InstantiatedTask]
    logs_result: FindLogsResult
    store: FlowStoreInternal | None
    store_config: FlowStoreConfig | None


def _prepare_run(spec: FlowSpec, base_dir: str, dry_run: bool) -> _RunContext:
    resolved_spec = resolve_spec(spec, base_dir=base_dir)
    # 470 - eval_resolve_tasks uses the display, which sets a global that causes it to be ignored when passed to eval_set
    # so we need to initialize the display type here first
    options = resolved_spec.options or FlowOptions()
    display_type = options.display or get_display_type()
    init_display_type(display_type)
    log_level = options.log_level or get_last_log_level()

    load_preload_files(resolved_spec)
    tasks = instantiate_tasks(resolved_spec, base_dir=base_dir)
    task_id_to_task = get_task_ids_to_tasks(tasks=tasks, spec=resolved_spec)
    store = store_factory(resolved_spec, base_dir=base_dir, create=True)
    store_config = (
        resolved_spec.store
        if isinstance(resolved_spec.store, FlowStoreConfig)
        else None
    )

    if store is None and store_config is not None:
        if store_config.read:
            flow_print("store_read has no effect: store is disabled", format="warning")
        if store_config.write and "write" in store_config.model_fields_set:
            flow_print("store_write has no effect: store is disabled", format="warning")

    if not resolved_spec.log_dir:
        raise ValueError("log_dir must be set before running the flow spec")

    if not dry_run:
        write_config_file(resolved_spec)

    logs_result = find_existing_logs(
        task_id_to_task,
        resolved_spec,
        store if (store_config is not None and store_config.read) else None,
        mode="dry_run" if dry_run else "run",
    )
    return _RunContext(
        spec=resolved_spec,
        options=options,
        display_type=display_type,
        log_level=log_level,
        tasks=tasks,
        logs_result=logs_result,
        store=store,
        store_config=store_config,
    )


def dry_run_eval_set(spec: FlowSpec, base_dir: str) -> FindLogsResult:
    return _prepare_run(spec, base_dir=base_dir, dry_run=True).logs_result


def run_eval_set(spec: FlowSpec, base_dir: str, dry_run: bool = False) -> LaunchResult:
    ctx = _prepare_run(spec, base_dir=base_dir, dry_run=dry_run)
    resolved_spec = ctx.spec
    assert resolved_spec.log_dir
    options = ctx.options
    task_log_info = ctx.logs_result.task_log_info

    with RunAction("evalset") as action:
        task_log = create_task_log_display(task_log_info, mode="pre-run")
        action.print(task_log.display)
        if option_str := _option_string(options):
            action.print("\nOptions:", option_str)
        action.print("")
        action.print(task_log.summary)
        action.print("Log dir:", path(resolved_spec.log_dir), copyable=True)
        if options.embed_viewer:
            print_url = apply_bundle_url_mappings(
                resolved_spec.log_dir, options.bundle_url_mappings
            )
            print_url = _ensure_trailing_slash(print_url)
            action.print("Viewer:", path(print_url), copyable=True)

    if dry_run:
        return LaunchResult(success=False, logs=[])

    title = display().get_title()
    if ctx.display_type == "full":
        content = display().make_renderable()
        if content is not None:
            set_flow_content(content)
    display().stop()

    update_log_level(ctx.log_level)

    eval_tasks = run_after_instantiate_hooks([t.task for t in ctx.tasks])

    start_time = time.time()
    result: LaunchResult | None
    try:
        success, logs = eval_set_call(
            resolved_spec,
            options,
            eval_tasks,
            display_type=ctx.display_type,
            log_level=ctx.log_level,
        )
        result = LaunchResult(success=success, logs=logs)
    except (KeyboardInterrupt, click.Abort):
        flow_print(Rule("Eval Set Interrupted"))
        result = None
    except Exception as e:
        if isinstance(e, PrerequisiteError):
            _fix_prerequisite_error_message(e)
        if error_string := str(e):
            flow_print(error_string, format="error")
        if hint := _stale_inspect_ai_hint():
            flow_print(hint, format="warning")
        flow_print(Rule("Eval Set Failed with Exception"))
        if error_string:
            raise FlowHandledError from e
        else:
            raise

    if not result:
        with ReadLogsProgress() as progress:
            dir_logs = list_all_eval_logs(
                log_dir=resolved_spec.log_dir, recursive=False, progress=progress
            )
            headers = [log.header for log in dir_logs]
            result = LaunchResult(success=False, logs=headers)

    elapsed_time = time.time() - start_time

    _print_result(resolved_spec, result, elapsed_time, task_log_info, title)

    if ctx.store and (ctx.store_config is None or ctx.store_config.write):
        # Now that the logs have been created, need to add the log_dir again to ensure all logs are indexed
        try:
            ctx.store.add_run_logs(result.logs)
        except NoLogsError as e:
            logger.error(
                f"No logs found in log directory: {resolved_spec.log_dir}. Cannot add to store. {e}"
            )

    return result


def _print_result(
    spec: FlowSpec,
    result: LaunchResult,
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
            info.eval_log = log

    task_log = create_task_log_display(task_log_info, mode="post-run")

    if title:
        spaced = [x for p in title for x in (" ", p)][1:]
        title_text = Text.assemble("[", *spaced, "]", end="")
    else:
        title_text = None

    output = [
        Text.assemble(
            summary, "\n", format_prefix("info"), " Total Time: ", elapsed, "\n"
        ),
        task_log.display,
        Text(""),
        task_log.summary,
    ]
    flow_print(
        Panel(
            Group(*output),
            title=title_text,
        ),
    )
    flow_print("Log dir:", path(spec.log_dir), soft_wrap=True, crop=False)
    if success:
        bundle_url_output = _bundle_url_output(spec)
        if bundle_url_output:
            flow_print(bundle_url_output, soft_wrap=True, crop=False)

    if num_success < len(logs):
        flow_print("Unsuccessful Tasks:")
        for log in logs:
            if log.status == "error":
                flow_print(
                    f"{log.eval.task}: {log.error.message if log.error else 'Unknown error'}",
                    format="error",
                )
            elif log.status != "success":
                flow_print(
                    f"{log.eval.task}: {log.status}",
                    format="warning",
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


def _min_inspect_ai_version() -> str | None:
    for req in requires("inspect_flow") or ():
        requirement = Requirement(req)
        if canonicalize_name(requirement.name) == "inspect-ai":
            for spec in requirement.specifier:
                if spec.operator in (">=", "=="):
                    return spec.version
    return None


def _stale_inspect_ai_hint() -> str | None:
    required = _min_inspect_ai_version()
    if required is None:
        return None
    try:
        installed = version("inspect-ai")
    except PackageNotFoundError:
        return None
    if Version(installed) >= Version(required):
        return None
    return (
        f"The installed inspect-ai ({installed}) is older than the required "
        f"inspect-ai >= {required}, which may be the cause of the error above. "
        f"Run `uv sync` (or otherwise upgrade inspect-ai to >= {required}) and retry."
    )


def _ensure_trailing_slash(url: str) -> str:
    if not url.endswith("/"):
        return url + "/"
    return url


def _bundle_url_output(spec: FlowSpec) -> Text | None:
    if not spec.options:
        return

    result = []

    if spec.options.bundle_dir:
        print_url = apply_bundle_url_mappings(
            spec.options.bundle_dir, spec.options.bundle_url_mappings
        )
        print_url = _ensure_trailing_slash(print_url)
        result.append("Bundle: ")
        result.append(path(print_url))

    if spec.options.embed_viewer and spec.log_dir:
        print_url = apply_bundle_url_mappings(
            spec.log_dir, spec.options.bundle_url_mappings
        )
        print_url = _ensure_trailing_slash(print_url)
        if result:
            result.append("\n")
        result.append("Viewer: ")
        result.append(path(print_url))

    return Text.assemble(*result) if result else None
