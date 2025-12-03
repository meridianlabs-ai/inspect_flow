from typing import Callable

INSPECT_FLOW_AFTER_LOAD_ATTR = "_inspect_flow_after_load"


def after_load(func: Callable) -> Callable:  # noqa: D417
    """Decorator to mark a function to be called after a FlowJob is loaded.

    The decorated function should have the signature (args are all optional and may be omitted):
        def after_flow_job_loaded(
            job: FlowJob,
            files: list[str],
        ) -> None:

        Args:
            job: The loaded FlowJob.
            files: List of file paths that were loaded to create the FlowJob.
        ...
    """  # noqa: D214,D417
    setattr(func, INSPECT_FLOW_AFTER_LOAD_ATTR, True)
    return func
