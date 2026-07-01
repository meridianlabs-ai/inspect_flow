import json
import os
from typing import Any

from inspect_ai._util.file import file


def run_handle(log_dir: str) -> dict[str, Any]:
    """Build a launch handle describing a run for external discovery.

    Args:
        log_dir: The (absolute) log directory the run writes to.

    Returns:
        A JSON-serializable handle with the run's `log_dir` and the process
        `pid` of the launching `flow run` command.
    """
    return {"log_dir": log_dir, "pid": os.getpid()}


def write_run_handle(handle_file: str, log_dir: str) -> dict[str, Any]:
    """Write a launch handle JSON file so a run can be discovered.

    A coding agent (or any external monitor) that backgrounds `flow run` can
    read this file to learn where the run is writing logs and which process to
    signal, without having to parse the interactive display.

    Args:
        handle_file: Path to write the handle JSON to.
        log_dir: The (absolute) log directory the run writes to.

    Returns:
        The handle that was written.
    """
    handle = run_handle(log_dir)
    with file(handle_file, "w") as f:
        f.write(json.dumps(handle, indent=2) + "\n")
    return handle
