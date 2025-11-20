from inspect_flow import FlowJob, FlowOptions

MAX_SAMPLES = 16

including_jobs: dict[str, FlowJob] = globals().get("__flow_including_jobs__", {})

for file, job in including_jobs.items():
    if (
        job.options
        and job.options.max_samples is not None
        and job.options.max_samples != MAX_SAMPLES
    ):
        raise ValueError(
            f"Do not override max samples! Error in {file} (or its includes)"
        )

my_config = FlowJob(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
