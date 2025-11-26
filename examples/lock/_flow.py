from inspect_flow import FlowJob, FlowOptions, including_jobs

MAX_SAMPLES = 16

# Validate that including configs don't override MAX_SAMPLES
for file, job in including_jobs().items():
    if (
        job.options
        and job.options.max_samples is not None
        and job.options.max_samples != MAX_SAMPLES
    ):
        raise ValueError(
            f"Do not override max_samples! Error in {file} (or its includes)"
        )

FlowJob(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
