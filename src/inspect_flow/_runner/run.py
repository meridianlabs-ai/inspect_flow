from typing import Any

import click
import inspect_ai
import yaml
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import file
from inspect_ai.log import EvalLog

from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._runner.resolve import resolve_job
from inspect_flow._types.flow_types import (
    FlowJob,
    FlowOptions,
    NotGiven,
    not_given,
)
from inspect_flow._util.list_util import sequence_to_list


def _read_config() -> FlowJob:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FlowJob.model_validate(data, extra="forbid")


def _print_resolved_config(job: FlowJob, base_dir: str) -> None:
    resolved_config = resolve_job(job, base_dir=base_dir)
    dump = config_to_yaml(resolved_config)
    click.echo(dump)


def _write_config_file(job: FlowJob) -> None:
    filename = f"{job.log_dir}/flow.yaml"
    yaml = config_to_yaml(job)
    with file(filename, "w") as f:
        f.write(yaml)


def _run_eval_set(
    job: FlowJob, base_dir: str, dry_run: bool = False
) -> tuple[bool, list[EvalLog]]:
    resolved_config = resolve_job(job, base_dir=base_dir)
    tasks = instantiate_tasks(resolved_config, base_dir=base_dir)

    if dry_run:
        click.echo(f"eval_set would be called with {len(tasks)} tasks")
        return False, []

    options = resolved_config.options or FlowOptions()
    if not resolved_config.log_dir:
        raise ValueError("log_dir must be set before running the flow job")

    _write_config_file(resolved_config)

    def ng(value: NotGiven | Any) -> Any:
        return value if value is not not_given else None

    try:
        result = inspect_ai.eval_set(
            tasks=tasks,
            log_dir=resolved_config.log_dir,
            retry_attempts=ng(options.retry_attempts),
            retry_wait=ng(options.retry_wait),
            retry_connections=ng(options.retry_connections),
            retry_cleanup=ng(options.retry_cleanup),
            # model= FlowTask
            # model_base_url= FlowModel
            # model_args= FlowModel
            # model_roles= FlowTask
            # task_args= FlowTask
            sandbox=ng(options.sandbox),
            sandbox_cleanup=ng(options.sandbox_cleanup),
            # solver= FlowTask
            tags=sequence_to_list(ng(options.tags)),
            metadata=ng(options.metadata),
            trace=ng(options.trace),
            display=ng(options.display),
            approval=ng(options.approval),
            score=ng(options.score) if ng(options.score) is not None else True,
            log_level=ng(options.log_level),
            log_level_transcript=ng(options.log_level_transcript),
            log_format=ng(options.log_format),
            limit=ng(options.limit),
            # sample_id= FlowTask
            sample_shuffle=ng(options.sample_shuffle),
            # epochs= FlowTask
            fail_on_error=ng(options.fail_on_error),
            continue_on_fail=ng(options.continue_on_fail),
            retry_on_error=ng(options.retry_on_error)
            if ng(options.retry_on_error) is not None
            else 3,
            debug_errors=ng(options.debug_errors),
            # message_limit= FlowTask
            # token_limit= FlowTask
            # time_limit= FlowTask
            # working_limit= FlowTask
            max_samples=ng(options.max_samples),
            max_tasks=ng(options.max_tasks)
            if ng(options.max_tasks) is not None
            else 10,
            max_subprocesses=ng(options.max_subprocesses),
            max_sandboxes=ng(options.max_sandboxes),
            log_samples=ng(options.log_samples),
            log_realtime=ng(options.log_realtime),
            log_images=ng(options.log_images),
            log_buffer=ng(options.log_buffer),
            log_shared=ng(options.log_shared),
            bundle_dir=ng(options.bundle_dir),
            bundle_overwrite=ng(options.bundle_overwrite) or False,
            log_dir_allow_dirty=ng(options.log_dir_allow_dirty),
            eval_set_id=ng(options.eval_set_id),
            # kwargs= FlowJob, FlowTask, and FlowModel allow setting the generate config
        )
    except PrerequisiteError as e:
        _fix_prerequisite_error_message(e)
        raise

    if result[0]:
        _print_bundle_url(resolved_config)

    return result


def _fix_prerequisite_error_message(e: PrerequisiteError) -> None:
    # Issue #217 - update error message to use 'bundle_overwrite' instead of 'overwrite'
    original_message = str(e.message)
    modified_message = original_message.replace("'overwrite'", "'bundle_overwrite'")
    if original_message != modified_message:
        e.message = modified_message

    if e.args:
        original_message = str(e.args[0])
        modified_message = original_message.replace("'overwrite'", "'bundle_overwrite'")
        if original_message != modified_message:
            e.args = (modified_message, *e.args[1:])


def _print_bundle_url(job: FlowJob) -> None:
    if job.options and job.options.bundle_url_map and job.options.bundle_dir:
        bundle_url = job.options.bundle_dir
        for local, url in job.options.bundle_url_map.items():
            bundle_url = bundle_url.replace(local, url)
        if bundle_url != job.options.bundle_dir:
            click.echo(f"Bundle URL: {bundle_url}")


@click.group(invoke_without_command=True)
@click.option(
    "--base-dir",
    type=str,
    default=False,
    help="Base directory.",
)
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    default=False,
    help="Dry run.",
)
@click.option(
    "--config",
    type=bool,
    is_flag=True,
    default=False,
    help="Output the resolved config and do not run.",
)
@click.pass_context
def flow_run(ctx: click.Context, base_dir: str, dry_run: bool, config: bool) -> None:
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    cfg = _read_config()
    if config:
        _print_resolved_config(cfg, base_dir=base_dir)
    else:
        _run_eval_set(cfg, base_dir=base_dir, dry_run=dry_run)


def main() -> None:
    flow_run()


if __name__ == "__main__":
    main()
