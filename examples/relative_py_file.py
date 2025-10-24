from inspect_flow._types.flow_types import FlowConfig

FlowConfig(
    {
        "log_dir": "logs/local_logs",
        "eval_set_options": {"limit": 1},
        "matrix": [
            {
                "tasks": [
                    {"name": "noop", "file": "local_eval/src/local_eval/noop.py"}
                ],
                "models": ["openai/gpt-4o-mini"],
            },
        ],
    }
)
