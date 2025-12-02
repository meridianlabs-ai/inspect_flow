from inspect_flow import FlowJob, FlowOptions

MAX_SAMPLES = 16


def after_flow_job_loaded(
    job: FlowJob, files_to_jobs: dict[str, FlowJob | None]
) -> None:
    """Validate that max_samples is set correctly."""
    if job.options and job.options.max_samples == MAX_SAMPLES:
        return
    # Determine which include file set max_samples
    for file, file_job in files_to_jobs.items():
        if (
            file_job
            and file_job.options
            and file_job.options.max_samples != MAX_SAMPLES
        ):
            raise ValueError(f"Do not override max_samples! Error in {file}.")
    raise ValueError("Do not override max_samples! Unable to determine file.")


my_config = FlowJob(
    options=FlowOptions(max_samples=MAX_SAMPLES),
)
