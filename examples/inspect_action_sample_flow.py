from inspect_flow._types.types import (
    Dependency,
    EvalSetOptions,
    FlowConfig,
    FlowOptions,
    Matrix,
    ModelConfig,
    TaskConfig,
)

# Example flow based on the sample config: https://github.com/METR/inspect-action/blob/main/examples/simple.eval-set.yaml


def flow_config() -> FlowConfig:
    return FlowConfig(
        options=FlowOptions(log_dir="./logs/inspect_action_sample"),
        eval_set_options=EvalSetOptions(limit=1),
        dependencies=[
            Dependency(package="openai"),
            Dependency(
                package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
            ),
        ],
        matrix=[
            Matrix(
                tasks=[
                    TaskConfig(name="inspect_evals/mbpp"),
                    TaskConfig(name="inspect_evals/class_eval"),
                ],
                models=[
                    ModelConfig(name="openai/gpt-4o-mini"),
                ],
            ),
        ],
    )
