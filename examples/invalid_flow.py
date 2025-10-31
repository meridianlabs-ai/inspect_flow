from inspect_flow._types.factories import flow_config, tasks

flow_config(
    {
        "flow_dir": "./logs/local_logs",
        "options": {"limit": 1},
        "dependencies": [
            "./examples/local_eval",
        ],
        "tasks": tasks(
            matrix={
                "name": ["local_eval/noop", "local_eval/noop2"],
                "model": [
                    "mockllm/mock-llm1",
                    "mockllm/mock-llm2",
                    {"name": "mockllm/mock-llm3", "version": "v1.0"},
                ],
            },
        ),
    }
)
