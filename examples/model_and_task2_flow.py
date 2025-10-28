from inspect_flow import flow_config

flow_config(
    {
        "flow_dir": "logs/model_and_task",
        "options": {"limit": 1},
        "dependencies": [
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
