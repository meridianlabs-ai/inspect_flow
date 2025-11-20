from inspect_flow import FlowJob, FlowOptions

MAX_SAMPLES = 16

including_jobs: list[FlowJob] = globals().get("__flow_including_jobs__", [])

for job in including_jobs:
    if (
        job.options
        and job.options.max_samples is not None
        and job.options.max_samples != MAX_SAMPLES
    ):
        raise ValueError("Do not override max samples!")

my_config = FlowJob(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
