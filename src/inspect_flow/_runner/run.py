import os

import click
import inspect_ai
import yaml
from inspect_ai.log import EvalLog

from inspect_flow._runner.matrix import instantiate_tasks
from inspect_flow._types.flow_types import (
    FlowConfig,
    FlowOptions,
)


def read_config() -> FlowConfig:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FlowConfig(**data)


def run_eval_set(config: FlowConfig) -> tuple[bool, list[EvalLog]]:
    tasks = instantiate_tasks(config)

    if os.environ.get("INSPECT_FLOW_DRY_RUN") == "1":
        click.echo(f"eval_set would be called with {len(tasks)} tasks")
        return False, []

    options = config.options or FlowOptions()
    return inspect_ai.eval_set(
        tasks=tasks,
        log_dir=config.flow_dir,
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
        score=options.score,
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
        # kwargs= FlowConfig, FlowTask, and FlowModel allow setting the generate config
    )


def main() -> None:
    config = read_config()
    run_eval_set(config)


if __name__ == "__main__":
    main()
