from inspect_flow import FlowJob, FlowOptions, FlowTask

FlowJob(
    log_dir="./logs/flow_test",
    options=FlowOptions(limit=1),
    tasks=[
        FlowTask(name="local_eval/noop", model="mockllm/mock-llm1"),
        FlowTask(name="local_eval/noop", model="mockllm/mock-llm1"),
    ],
)
