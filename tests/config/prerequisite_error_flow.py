from inspect_flow import FlowDependencies, FlowJob, FlowOptions, FlowTask

FlowJob(
    log_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    dependencies=FlowDependencies(
        additional_dependencies=[
            "../local_eval",
        ]
    ),
    tasks=[
        FlowTask(name="local_eval/noop", model="mockllm/mock-llm1"),
        FlowTask(name="local_eval/noop", model="mockllm/mock-llm1"),
    ],
)
