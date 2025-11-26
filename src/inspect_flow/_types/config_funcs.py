"""Functions for use in Flow config files."""

from inspect_flow._types.flow_types import FlowJob

_including_jobs: dict[str, FlowJob] = {}


def set_including_jobs(jobs: dict[str, FlowJob] | None) -> None:
    global _including_jobs
    _including_jobs = jobs or {}


def including_jobs() -> dict[str, FlowJob]:
    """Get the list of FlowJobs that are currently being loaded.

    Returns:
        A dictionary mapping file paths to FlowJobs.
    """
    return _including_jobs
