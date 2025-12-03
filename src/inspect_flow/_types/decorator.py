from typing import Callable

INSPECT_FLOW_AFTER_LOAD_ATTR = "_inspect_flow_after_load"


def after_load(func: Callable) -> Callable:
    """Decorator to mark a function to be called after a FlowJob is loaded.

    The decorated function should have the signature (args are all optional and may be omitted):
        def after_flow_job_loaded(
            job: FlowJob,
            files_to_jobs: dict[str, FlowJob | None],
        ) -> None:
        ...
    """
    setattr(func, INSPECT_FLOW_AFTER_LOAD_ATTR, True)
    return func
