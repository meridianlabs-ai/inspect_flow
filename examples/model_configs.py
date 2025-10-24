from inspect_flow._types.flow_types import FlowConfig

FlowConfig(
    {
        "log_dir": "logs/model_configs",
        "eval_set_options": {"limit": 1},
        "dependencies": [
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        "matrix": [
            {
                "tasks": ["inspect_evals/mmlu_0_shot"],
                "models": [
                    {
                        "name": "openai/gpt-4o-mini",
                        "config": [{"temperature": 0}, {"temperature": 0.7}],
                    }
                ],
            },
        ],
    }
)
