from inspect_flow._types.flow_types import FlowConfig

FlowConfig(
    {
        "log_dir": "logs/solvers",
        "eval_set_options": {"limit": 1},
        "dependencies": [
            "-e /Users/ransomrichardson/git/inspect_ai",
            "git+https://github.com/UKGovernmentBEIS/inspect_evals@dac86bcfdc090f78ce38160cef5d5febf0fb3670",
        ],
        "matrix": [
            {
                "tasks": ["inspect_evals/mmlu_0_shot"],
                "solvers": [
                    {
                        "name": "inspect_ai/system_message",
                        "args": [
                            {"template": "test system message"},
                            {"template": "another test system message"},
                        ],
                    },
                    [
                        {
                            "name": "inspect_ai/system_message",
                            "args": [{"template": "test system message"}],
                        },
                        {"name": "inspect_ai/generate"},
                    ],
                ],
                "models": [
                    {
                        "name": "openai/gpt-4o-mini",
                    }
                ],
            },
        ],
    }
)
