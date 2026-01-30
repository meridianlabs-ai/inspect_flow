import time
from datetime import timedelta
from logging import getLogger

import click
import yaml
from inspect_ai import eval_set
from inspect_ai._eval.eval import eval_resolve_tasks
from inspect_ai._eval.evalset import EvalSetArgsInTaskIdentifier, task_identifier
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import file
from inspect_ai.log import EvalLog
from inspect_ai.model import GenerateConfig, get_model
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax

from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.instantiate import InstantiatedTask, instantiate_tasks
from inspect_flow._runner.resolve import resolve_spec
from inspect_flow._types.flow_types import (
    FlowOptions,
    FlowSpec,
    FlowTask,
)
from inspect_flow._util.console import format_prefix, path, print, quantity
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.list_util import sequence_to_list
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.not_given import default, default_none
from inspect_flow._util.pydantic_util import model_dump
from inspect_flow._util.subprocess_util import signal_ready_and_wait

logger = getLogger(__file__)


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
    resolved_config = resolve_spec(spec, base_dir=base_dir)
    tasks = instantiate_tasks(resolved_config, base_dir=base_dir)
    _ = _get_task_ids(tasks=tasks, spec=resolved_config)

    if dry_run:
        dump = config_to_yaml(resolved_config)
        yaml_syntax = Syntax(dump, "yaml", theme="monokai", background_color="default")
        print(" ", Rule("Resolved configuration as YAML"), yaml_syntax)
        return False, []

    options = resolved_config.options or FlowOptions()
    if not resolved_config.log_dir:
        raise ValueError("log_dir must be set before running the flow spec")

    _write_config_file(resolved_config)

    print(f"\nRunning {quantity(len(tasks), 'task')}")
    print(f"Using log directory: {path(resolved_config.log_dir)}\n", format="info")

    print(Rule("Begin Eval Set Execution"))
    start_time = time.time()
    try:
        result = eval_set(
            tasks=[t.task for t in tasks],
            log_dir=resolved_config.log_dir,
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
    except PrerequisiteError as e:
        _fix_prerequisite_error_message(e)
        raise
    finally:
        print(Rule("End Eval Set Execution"))
    elapsed_time = time.time() - start_time

    _print_result(resolved_config, result, elapsed_time)

    if result[0]:
        _print_bundle_url(resolved_config)

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
    print(
        "\n",
        Panel(
            f"""\
{summary}

Total Time: {elapsed}
{tasks}
Log Directory: {path(spec.log_dir)}"""
        ),
    )

    if num_success < len(logs):
        print("\nFailed Tasks:")
        for log in logs:
            if log.status == "error":
                print(
                    f"{log.eval.task}: {log.error.message if log.error else 'Unknown error'}",
                    format="error",
                )


def _get_task_ids(tasks: list[InstantiatedTask], spec: FlowSpec) -> set[str]:
    if not tasks:
        return set()

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

    task_ids = set()
    for i, task in enumerate(resolved_tasks):
        task_id = task_identifier(
            task=task,
            eval_set_args=EvalSetArgsInTaskIdentifier(config=GenerateConfig()),
        )
        if task_id in task_ids:
            flow_task = tasks[i].flow_task
            if isinstance(flow_task, FlowTask):
                task_json = model_dump(flow_task)
                raise ValueError(f"Duplicate task found: {task_json}")
            else:
                raise ValueError(f"Duplicate task found: {task}")

        task_ids.add(task_id)
    return task_ids


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
            click.echo(f"Bundle URL: {bundle_url}")


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
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        raise NotImplementedError("Run has no subcommands.")

    init_flow_logging(log_level=log_level)
    signal_ready_and_wait()

    cfg = _read_config(file)
    run_eval_set(cfg, base_dir=base_dir, dry_run=dry_run)


if __name__ == "__main__":
    flow_run()
