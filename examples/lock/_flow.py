from inspect_flow import FlowJob, FlowOptions

MAX_SAMPLES = 16

# Get all configs that are including this one
including_jobs: dict[str, FlowJob] = globals().get("__flow_including_jobs__", {})

# Validate that including configs don't override MAX_SAMPLES
for file, job in including_jobs.items():
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
