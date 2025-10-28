import inspect_ai
import yaml
from inspect_ai.log import EvalLog

from inspect_flow._runner.matrix import MatrixImpl
from inspect_flow._types.flow_types import (
    FlowConfig,
    FlowOptions,
)


def read_config() -> FlowConfig:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FlowConfig(**data)


def run_eval_set(config: FlowConfig) -> tuple[bool, list[EvalLog]]:
    matrix_list = [MatrixImpl(matrix_config, config) for matrix_config in config.matrix]
    tasks = [task for matrix in matrix_list for task in matrix.tasks()]

    options = config.options or FlowOptions()
    return inspect_ai.eval_set(
        tasks=tasks,
        log_dir=config.flow_dir,
        retry_attempts=options.retry_attempts,
        retry_wait=options.retry_wait,
        retry_connections=options.retry_connections,
        retry_cleanup=options.retry_cleanup,
        # model= Matrix or Task
        # model_base_url= ModelConfig
        # model_args= ModelConfig
        # model_roles= Matrix or Task
        # task_args= Matrix or Task
        sandbox=options.sandbox,
        sandbox_cleanup=options.sandbox_cleanup,
        # solver= Matrix or Task
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
        # sample_id= TaskConfig
        sample_shuffle=options.sample_shuffle,
        # epochs= TaskConfig
        fail_on_error=options.fail_on_error,
        continue_on_fail=options.continue_on_fail,
        retry_on_error=options.retry_on_error,
        debug_errors=options.debug_errors,
        # message_limit= TaskConfig
        # token_limit= TaskConfig
        # time_limit= TaskConfig
        # working_limit= TaskConfig
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
        # kwargs= FlowConfig, TaskConfig, and ModelConfig allow setting the generate config
    )


def main() -> None:
    config = read_config()
    run_eval_set(config)


if __name__ == "__main__":
    main()
