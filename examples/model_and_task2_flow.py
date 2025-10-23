from inspect_flow._types.flow_types import FlowConfig

flow_config = FlowConfig(
    {
        "log_dir": "model_and_task",
        "eval_set_options": {"limit": 1},
        "dependencies": [
            "openai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        "matrix": [
            {
                "tasks": ["inspect_evals/mmlu_0_shot"],
                "models": ["openai/gpt-4o-mini"],
            },
        ],
    }
)
