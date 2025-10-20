import inspect_ai
import yaml
from inspect_ai.log import EvalLog

from inspect_flow._runner.matrix import MatrixImpl
from inspect_flow._types.types import (
    FlowConfig,
    FlowOptions,
    RetryOptions,
    SandboxOptions,
)


def read_config() -> FlowConfig:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FlowConfig(**data)


def run_eval_set(config: FlowConfig) -> tuple[bool, list[EvalLog]]:
    matrix_list = [MatrixImpl(matrix_config) for matrix_config in config.matrix]
    tasks = [task for matrix in matrix_list for task in matrix.tasks()]

    options = config.options or FlowOptions(log_dir=".")
    retry_options = config.retry_options or RetryOptions()
    sandbox_options = config.sandbox_options or SandboxOptions()

    return inspect_ai.eval_set(
        tasks=tasks,
        log_dir=options.log_dir,
        retry_attempts=retry_options.retry_attempts,
        retry_wait=retry_options.retry_wait,
        retry_connections=retry_options.retry_connections,
        retry_cleanup=retry_options.retry_cleanup,
        # model= Matrix or Task
        # model_base_url= ModelConfig
        # model_args= ModelConfig
        # model_roles= Matrix or Task
        # task_args= Matrix or Task
        sandbox=sandbox_options.sandbox,
        sandbox_cleanup=sandbox_options.sandbox_cleanup,
        # solver= Matrix or Task
        tags=options.tags,
        metadata=options.metadata,
        trace=options.trace,
        display=options.display,
        approval=options.approval,
        score=options.score,
        log_level=options.log_level,
        log_level_transcript=options.log_level_transcript,
        log_format=options.log_format,
        limit=options.limit,
        # sample_id= TaskConfig
        sample_shuffle=options.sample_shuffle,
        # epochs= TaskConfig
        # fail_on_error= TaskConfig
        # continue_on_fail= TaskConfig
        retry_on_error=retry_options.retry_on_error,
        debug_errors=options.debug_errors,
    )


def main() -> None:
    config = read_config()
    run_eval_set(config)


if __name__ == "__main__":
    main()
