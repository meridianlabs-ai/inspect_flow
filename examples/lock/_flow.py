from inspect_flow import FlowJob, FlowOptions, after_load

MAX_SAMPLES = 16


@after_load
def validate_max_samples(job: FlowJob) -> None:
    if not job.options or not job.options.max_samples == MAX_SAMPLES:
        raise ValueError("Do not override max_samples!")


FlowJob(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
