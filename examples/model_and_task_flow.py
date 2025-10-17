from inspect_flow._types.types import (
    Dependency,
    FlowConfig,
    FlowOptions,
    Matrix,
    ModelConfig,
    TaskConfig,
)


def flow_config() -> FlowConfig:
    return FlowConfig(
        options=FlowOptions(log_dir="model_and_task", limit=1),
        dependencies=[
            Dependency(package="openai"),
            Dependency(
                package="git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670"
            ),
        ],
        matrix=[
            Matrix(
                tasks=[
                    TaskConfig(name="inspect_evals/mmlu_0_shot"),
                ],
                models=[
                    ModelConfig(name="openai/gpt-4o-mini"),
                ],
            ),
        ],
    )
