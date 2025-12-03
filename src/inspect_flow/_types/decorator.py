from typing import Callable

INSPECT_FLOW_AFTER_LOAD_ATTR = "_inspect_flow_after_load"


def after_load(func: Callable) -> Callable:
    """Decorator to mark a function to be called after a FlowJob is loaded.

    The decorated function should have the signature (args are all optional and may be omitted):
    def after_flow_job_loaded(
        job: FlowJob,
        files: list[str],
    ) -> None:

        job: The loaded FlowJob.
        files: List of file paths that were loaded to create the FlowJob.
    ...

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.

    """
    setattr(func, INSPECT_FLOW_AFTER_LOAD_ATTR, True)
    return func
