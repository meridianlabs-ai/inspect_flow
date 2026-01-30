"""Utilities for running subprocesses with logging support."""

import os
import subprocess
from logging import getLogger
from typing import Any

logger = getLogger(__name__)

# Environment variable names for passing synchronization fd numbers to child.
# The parent sets these before spawning the child process.
CHILD_READY_FD_ENV = "INSPECT_FLOW_CHILD_READY_FD"
PARENT_ACK_FD_ENV = "INSPECT_FLOW_PARENT_ACK_FD"


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
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )

    return result
