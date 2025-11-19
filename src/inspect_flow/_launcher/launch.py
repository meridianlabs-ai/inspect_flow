import pathlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import click
from inspect_ai._util.file import exists

from inspect_flow._launcher.venv import create_venv
from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.path_util import absolute_path, set_cwd_env_var


def launch(
    job: FlowJob,
    run_args: list[str] | None = None,
) -> None:
    if not job.log_dir:
        raise ValueError("log_dir must be set before launching the flow job")

    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)
    set_cwd_env_var()
    job.log_dir = _resolve_log_dir(job)
    if job.options and job.options.bundle_dir:
        job.options.bundle_dir = absolute_path(job.options.bundle_dir)
    click.echo(f"Using log_dir: {job.log_dir}")

    with tempfile.TemporaryDirectory(dir=temp_dir_parent) as temp_dir:
        env = create_venv(job, temp_dir)
        if job.env:
            env.update(**job.env)

        python_path = Path(temp_dir) / ".venv" / "bin" / "python"
        run_path = (Path(__file__).parents[1] / "_runner" / "run.py").absolute()
        try:
            subprocess.run(
                [str(python_path), str(run_path), *(run_args or [])],
                cwd=temp_dir,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)


def _resolve_log_dir(job: FlowJob) -> str:
    assert job.log_dir
    absolute_log_dir = absolute_path(job.log_dir)

    if job.new_log_dir:
        return _new_log_dir(absolute_log_dir)
    else:
        return absolute_log_dir


def _new_log_dir(log_dir: str) -> str:
    if not exists(log_dir):
        return log_dir

    # Check if log_dir ends with _<number>
    match = re.match(r"^(.+)_(\d+)$", log_dir)
    if match:
        base_log_dir = match.group(1)
        suffix = int(match.group(2)) + 1  # Start from next suffix
    else:
        base_log_dir = log_dir
        suffix = 1

    # Find the next available directory
    current_dir = f"{base_log_dir}_{suffix}"
    while exists(current_dir):
        suffix += 1
        current_dir = f"{base_log_dir}_{suffix}"
    return current_dir
