from inspect_flow import FlowJob, FlowOptions, FlowTask

FlowJob(
    log_dir="logs/my_eval",
    options=FlowOptions(
        bundle_dir="s3://my-bucket/bundles/my_eval",
        bundle_url_mappings={"s3://my-bucket": "https://my-bucket.s3.amazonaws.com"},
    ),
    tasks=[FlowTask(name="task", model="openai/gpt-4o")],
)
