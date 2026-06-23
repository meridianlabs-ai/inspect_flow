"""Utilities for running subprocesses with logging support."""

import json
import os
import subprocess
from logging import getLogger
from pathlib import Path
from typing import Any

from inspect_flow._util.console import flow_print

logger = getLogger(__name__)

# Environment variable names for passing synchronization fd numbers to child.
# The parent sets these before spawning the child process.
CHILD_READY_FD_ENV = "INSPECT_FLOW_CHILD_READY_FD"
PARENT_ACK_FD_ENV = "INSPECT_FLOW_PARENT_ACK_FD"

# Absolute path of a per-run file the child writes its success flag to. The
# parent creates the path and sets this before spawning the child. Using an
# explicit per-run path (rather than a shared key) keeps concurrent runs from
# racing and is unaffected by env changes to the child's HOME/XDG_DATA_HOME.
RUN_RESULT_FILE_ENV = "INSPECT_FLOW_RUN_RESULT_FILE"


def write_run_result(success: bool) -> None:
    """Write the run success flag to the per-run result file, if one was set.

    Called by a child runner process spawned with `RUN_RESULT_FILE_ENV`. Does
    nothing when the env var is unset (e.g. when invoked standalone).

    Args:
        success: Whether the eval set completed successfully.
    """
    result_path = os.environ.get(RUN_RESULT_FILE_ENV)
    if result_path:
        Path(result_path).write_text(json.dumps({"success": success}))


def read_run_result(result_path: str) -> bool:
    """Read the success flag a child runner wrote to its per-run result file.

    Args:
        result_path: Absolute path the child was told to write to.

    Returns:
        The success flag written by the child.

    Raises:
        RuntimeError: If the child exited without writing a result.
    """
    path = Path(result_path)
    if not path.exists():
        raise RuntimeError(
            f"venv run process exited without reporting a result at {result_path}"
        )
    return bool(json.loads(path.read_text())["success"])


def signal_ready_and_wait() -> None:
    """Signal parent process we're ready, then wait for acknowledgment.

    This should be called early in a child process that was spawned with
    the synchronization fds passed via pass_fds and the fd numbers set in
    environment variables. If the env vars aren't set (e.g., running
    standalone), this function does nothing.
    """
    child_ready_fd_str = os.environ.get(CHILD_READY_FD_ENV)
    parent_ack_fd_str = os.environ.get(PARENT_ACK_FD_ENV)

    if not child_ready_fd_str or not parent_ack_fd_str:
        return  # Not spawned with synchronization fds

    try:
        child_ready_fd = int(child_ready_fd_str)
        parent_ack_fd = int(parent_ack_fd_str)

        os.write(child_ready_fd, b"r")
        os.close(child_ready_fd)
        os.read(parent_ack_fd, 1)
        os.close(parent_ack_fd)
    except (OSError, ValueError) as e:
        logger.warning(f"Parent-child synchronization failed: {e}")


def run_with_logging(
    args: list[str],
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    log_output: bool = True,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run subprocess command and log stdout/stderr.

    Args:
        args: Command and arguments to run
        cwd: Working directory for the command
        env: Environment variables
        check: If True, raise CalledProcessError on non-zero exit
        log_output: If True, log stdout and stderr to logger
        **kwargs: Additional arguments passed to subprocess.run

    Returns:
        CompletedProcess instance with stdout/stderr as strings

    Raises:
        CalledProcessError: If check=True and command returns non-zero exit code
    """
    # Ensure we capture output as text
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)

    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,  # Handle errors manually to log before raising
        **kwargs,
    )

    if log_output:
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                logger.debug(line)

        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                logger.debug(line)

    # Check return code after logging
    if check and result.returncode != 0:
        flow_print(
            f"Command {' '.join(args)} failed with exit code {result.returncode}",
            format="error",
        )
        if result.stderr:
            flow_print(result.stderr, format="error")
        else:
            flow_print(result.stdout, format="error")
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )

    return result
