import subprocess
from pathlib import Path

from inspect_flow import FlowJob


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


def after_flow_job_loaded(files_to_jobs: dict[str, FlowJob | None]) -> None:
    # Check no config files are in a dirty git repo
    for path in files_to_jobs.keys():
        check_repo(path)
