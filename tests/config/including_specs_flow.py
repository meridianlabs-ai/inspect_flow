from inspect_flow import FlowOptions, FlowSpec, after_load

MAX_SAMPLES = 16


@after_load
def validate_max_samples(spec: FlowSpec) -> None:
    """Validate that max_samples is set correctly."""
    if not spec.options or not spec.options.max_samples == MAX_SAMPLES:
        raise ValueError("Do not override max_samples!")


my_config = FlowSpec(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
