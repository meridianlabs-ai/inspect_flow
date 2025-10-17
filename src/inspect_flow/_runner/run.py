import inspect_ai
import yaml
from inspect_ai.log import EvalLog

from inspect_flow._runner.matrix import MatrixImpl
from inspect_flow._types.types import (
    FlowConfig,
    FlowOptions,
)


def read_config() -> FlowConfig:
    with open("flow.yaml", "r") as f:
        data = yaml.safe_load(f)
        return FlowConfig(**data)


def run_eval_set(config: FlowConfig) -> tuple[bool, list[EvalLog]]:
    matrix = MatrixImpl(config.matrix)
    options = config.options or FlowOptions(log_dir=".")
    return inspect_ai.eval_set(
        tasks=matrix.tasks(),
        log_dir=options.log_dir,
        limit=options.limit,
    )


def main() -> None:
    config = read_config()
    run_eval_set(config)


if __name__ == "__main__":
    main()
