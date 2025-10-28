from inspect_flow import flow_config

flow_config(
    {
        "flow_dir": "logs/local_logs",
        "options": {"limit": 1},
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
