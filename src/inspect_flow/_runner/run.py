import click
import inspect_ai
import yaml
from inspect_ai._util.dateutil import iso_now
from inspect_ai._util.file import clean_filename_component, file
from inspect_ai.log import EvalLog

from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.instantiate import instantiate_tasks
from inspect_flow._runner.resolve import resolve_config
from inspect_flow._types.flow_types import (
    FConfig,
    FOptions,
)


def _read_config() -> FConfig:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FConfig(**data)


def _print_resolved_config(config: FConfig) -> None:
    resolved_config = resolve_config(config)
    dump = config_to_yaml(resolved_config)
    click.echo(dump)


def _write_config_file(config: FConfig) -> None:
    filename = f"{config.flow_dir}/{clean_filename_component(iso_now())}_flow.yaml"
    yaml = config_to_yaml(config)
    with file(filename, "w") as f:
        f.write(yaml)


def _run_eval_set(config: FConfig, dry_run: bool = False) -> tuple[bool, list[EvalLog]]:
    resolved_config = resolve_config(config)
    tasks = instantiate_tasks(resolved_config)

    if dry_run:
        click.echo(f"eval_set would be called with {len(tasks)} tasks")
        return False, []

    options = config.options or FOptions()
    assert config.flow_dir, "flow_dir must be set before calling run_eval_set"

    _write_config_file(resolved_config)

    log_dir = config.flow_dir + "/logs"
    log_dir_allow_dirty = (
        options.log_dir_allow_dirty if options.log_dir_allow_dirty is not None else True
    )

    return inspect_ai.eval_set(
        tasks=tasks,
        log_dir=log_dir,
        retry_attempts=options.retry_attempts,
        retry_wait=options.retry_wait,
        retry_connections=options.retry_connections,
        retry_cleanup=options.retry_cleanup,
        # model= FlowTask
        # model_base_url= FlowModel
        # model_args= FlowModel
        # model_roles= FlowTask
        # task_args= FlowTask
        sandbox=options.sandbox,
        sandbox_cleanup=options.sandbox_cleanup,
        # solver= FlowTask
        tags=options.tags,
        metadata=options.metadata,
        trace=options.trace,
        display=options.display,
        approval=options.approval,  # type: ignore TODO:ransom
        score=options.score or True,
        log_level=options.log_level,
        log_level_transcript=options.log_level_transcript,
        log_format=options.log_format,
        limit=options.limit,
        # sample_id= FlowTask
        sample_shuffle=options.sample_shuffle,
        # epochs= FlowTask
        fail_on_error=options.fail_on_error,
        continue_on_fail=options.continue_on_fail,
        retry_on_error=options.retry_on_error,
        debug_errors=options.debug_errors,
        # message_limit= FlowTask
        # token_limit= FlowTask
        # time_limit= FlowTask
        # working_limit= FlowTask
        max_samples=options.max_samples,
        max_tasks=options.max_tasks,
        max_subprocesses=options.max_subprocesses,
        max_sandboxes=options.max_sandboxes,
        log_samples=options.log_samples,
        log_realtime=options.log_realtime,
        log_images=options.log_images,
        log_buffer=options.log_buffer,
        log_shared=options.log_shared,
        # bundle_dir= Not supported
        # bundle_overwrite= Not supported
        log_dir_allow_dirty=log_dir_allow_dirty,
        # kwargs= FlowConfig, FlowTask, and FlowModel allow setting the generate config
    )


@click.group(invoke_without_command=True)
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
def flow_run(ctx: click.Context, dry_run: bool, config: bool) -> None:
    # if this was a subcommand then allow it to execute
    if ctx.invoked_subcommand is not None:
        return

    cfg = _read_config()
    if config:
        _print_resolved_config(cfg)
    else:
        _run_eval_set(cfg, dry_run=dry_run)


def main() -> None:
    flow_run()


if __name__ == "__main__":
    main()
