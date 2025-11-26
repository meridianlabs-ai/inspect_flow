import subprocess
from pathlib import Path

from inspect_flow import FlowJob, including_jobs


def check_repo(path: str) -> None:
    abs_path = Path(path).resolve()
    check_dir = abs_path if abs_path.is_dir() else abs_path.parent

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=check_dir,
        capture_output=True,
        text=True,
        check=True,
    )

    if result.stdout.strip():
        raise RuntimeError(f"The repository at {check_dir} has uncommitted changes.")


# Check this config and all configs including it
check_repo(__file__)
for path in including_jobs().keys():
    check_repo(path)

FlowJob()  # Return empty job for inheritance
