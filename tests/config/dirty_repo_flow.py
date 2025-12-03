"""Test to ensure that included configs are in clean git repos."""

import subprocess
from pathlib import Path

from inspect_flow import after_load


def check_repo(path: str) -> None:
    # Convert to absolute path and get the directory
    abs_path = Path(path).resolve()
    check_dir = abs_path if abs_path.is_dir() else abs_path.parent

    try:
        # Run git status --porcelain to get uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=check_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        # If output is non-empty, there are uncommitted changes
        if bool(result.stdout.strip()):
            raise RuntimeError(
                f"The repository at {check_dir} has uncommitted changes."
            )
    except subprocess.CalledProcessError as e:
        # Check if it's because we're not in a git repository
        if "not a git repository" in e.stderr.lower():
            raise RuntimeError(
                f"The directory {check_dir} is not a git repository."
            ) from e
        # Re-raise other git errors
        raise
    except FileNotFoundError as e:
        # git command not found
        raise RuntimeError("Git command not found. Is git installed?") from e


@after_load
def validate_no_dirty_repo(files: list[str]) -> None:
    # Check no config files are in a dirty git repo
    for path in files:
        check_repo(path)
