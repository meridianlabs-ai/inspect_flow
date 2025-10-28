from inspect_flow._types.flow_types import flow_config

flow_config(
    {
        "log_dir": "logs/local_logs",
        "eval_set_options": {"limit": 1},
        "matrix": [
            {
                "tasks": [
                    {"name": "noop", "file": "local_eval/src/local_eval/noop.py"}
                ],
                "models": ["mockllm/mock-llm"],
            },
        ],
    }
)
