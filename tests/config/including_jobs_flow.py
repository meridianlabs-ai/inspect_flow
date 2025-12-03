from inspect_flow import FlowJob, FlowOptions, after_load

MAX_SAMPLES = 16


@after_load
def validate_max_samples(job: FlowJob) -> None:
    """Validate that max_samples is set correctly."""
    if not job.options or not job.options.max_samples == MAX_SAMPLES:
        raise ValueError("Do not override max_samples!")


my_config = FlowJob(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
