from inspect_flow import FlowOptions, FlowSpec, after_load

MAX_SAMPLES = 16


@after_load
def validate_max_samples(job: FlowSpec) -> None:
    if not job.options or not job.options.max_samples == MAX_SAMPLES:
        raise ValueError("Do not override max_samples!")


FlowSpec(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
