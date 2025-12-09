"""Utilities for running subprocesses with logging support."""

import subprocess
from logging import getLogger
from typing import Any

logger = getLogger(__name__)


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
        # Log stdout at INFO level
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                logger.info(line)

        # Log stderr at INFO level
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                logger.info(line)

    # Check return code after logging
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )

    return result
