from inspect_flow import flow_config

flow_config(
    {
        "flow_dir": "logs/local_logs",
        "options": {"limit": 1},
        "tasks": [
            {
                "name": "local_eval/src/local_eval/noop.py@noop",
                "model": "mockllm/mock-llm",
            },
        ],
    }
)
