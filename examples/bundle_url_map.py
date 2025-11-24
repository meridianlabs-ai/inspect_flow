from inspect_flow import FlowJob, FlowOptions, FlowTask

FlowJob(
    log_dir="logs/my_eval",
    options=FlowOptions(
        bundle_dir="/local/storage/bundles/my_eval",
        bundle_url_map={"/local/storage": "https://example.com/shared"},
    ),
    tasks=[FlowTask(name="task", model="openai/gpt-4o")],
)
