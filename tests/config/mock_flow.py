from inspect_flow import FlowOptions, FlowSpec, FlowTask

my_config = FlowSpec(
    log_dir="logs/mock_flow",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(
            name="inspect_evals/gpqa_diamond",
            model="mockllm/mock-llm",
        )
    ],
)
