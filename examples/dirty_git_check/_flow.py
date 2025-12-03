import subprocess
from pathlib import Path

from inspect_flow import after_load


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


@after_load
def validate_no_dirty_repo(files: list[str]) -> None:
    # Check no config files are in a dirty git repo
    for path in files:
        check_repo(path)
