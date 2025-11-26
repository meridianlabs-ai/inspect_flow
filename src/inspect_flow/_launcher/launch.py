import re
import subprocess
import sys
import tempfile
from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path, exists

from inspect_flow._launcher.venv import create_venv, write_flow_yaml
from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.path_util import absolute_path_relative_to


def launch(
    job: FlowJob,
    base_dir: str,
    env: dict[str, str],
    run_args: list[str] | None = None,
    no_venv: bool = False,
) -> None:
    if not job.log_dir:
        raise ValueError("log_dir must be set before launching the flow job")

    job.log_dir = _resolve_log_dir(job, base_dir=base_dir)
    if job.options and job.options.bundle_dir:
        # Ensure bundle_dir and bundle_url_map are absolute paths
        job.options.bundle_dir = absolute_path_relative_to(
            job.options.bundle_dir, base_dir=base_dir
        )
        if job.options.bundle_url_map:
            job.options.bundle_url_map = {
                absolute_path_relative_to(k, base_dir=base_dir): v
                for k, v in job.options.bundle_url_map.items()
            }
    click.echo(f"Using log_dir: {job.log_dir}")

    run_path = (Path(__file__).parents[1] / "_runner" / "run.py").absolute()
    base_dir = absolute_file_path(base_dir)
    args = ["--base-dir", base_dir] + (run_args or [])
    if job.env:
        env.update(**job.env)

    if no_venv:
        python_path = sys.executable
        file = write_flow_yaml(job, ".")
        try:
            subprocess.run(
                [str(python_path), str(run_path), *args], check=True, env=env
            )
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        finally:
            file.unlink(missing_ok=True)
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        # Set the virtual environment so that it will be created in the temp directory
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")

        create_venv(job, base_dir=base_dir, temp_dir=temp_dir, env=env)

        python_path = Path(temp_dir) / ".venv" / "bin" / "python"
        try:
            subprocess.run(
                [str(python_path), str(run_path), *args],
                cwd=temp_dir,
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)


def _resolve_log_dir(job: FlowJob, base_dir: str) -> str:
    assert job.log_dir
    absolute_log_dir = absolute_path_relative_to(job.log_dir, base_dir=base_dir)

    if job.log_dir_create_unique:
        return _log_dir_create_unique(absolute_log_dir)
    else:
        return absolute_log_dir


def _log_dir_create_unique(log_dir: str) -> str:
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
