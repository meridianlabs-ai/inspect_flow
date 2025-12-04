import os
import subprocess
import sys
import tempfile
from logging import getLogger
from pathlib import Path

from dotenv import dotenv_values, find_dotenv
from inspect_ai._util.file import absolute_file_path

from inspect_flow._launcher.venv import create_venv, write_flow_yaml
from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(__name__)


def launch(
    job: FlowJob,
    base_dir: str,
    no_dotenv: bool = False,
    run_args: list[str] | None = None,
    no_venv: bool = False,
) -> None:
    env = _get_env(base_dir, no_dotenv)

    if not job.log_dir:
        raise ValueError("log_dir must be set before launching the flow job")
    job.log_dir = absolute_path_relative_to(job.log_dir, base_dir=base_dir)

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
    logger.info(f"Using log_dir: {job.log_dir}")

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
        finally:
            file.unlink(missing_ok=True)
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        # Set the virtual environment so that it will be created in the temp directory
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")

        create_venv(job, base_dir=base_dir, temp_dir=temp_dir, env=env)

        python_path = Path(temp_dir) / ".venv" / "bin" / "python"
        subprocess.run(
            [str(python_path), str(run_path), *args],
            cwd=temp_dir,
            check=True,
            env=env,
        )


def _get_env(base_dir: str, no_dotenv: bool) -> dict[str, str]:
    env = os.environ.copy()
    if no_dotenv:
        return env
    # Temporarily change to base_dir to find .env file
    original_cwd = os.getcwd()
    try:
        os.chdir(base_dir)
        # Already loaded environment variables should take precedence
        dotenv = dotenv_values(find_dotenv(usecwd=True))
        env = {k: v for k, v in dotenv.items() if v is not None} | env
    finally:
        os.chdir(original_cwd)
    return env
