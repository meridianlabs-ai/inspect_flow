import os
import subprocess
import sys
import tempfile
from logging import getLogger
from pathlib import Path

import yaml
from dotenv import dotenv_values, find_dotenv
from inspect_ai._util.file import absolute_file_path

from inspect_flow._launcher.venv import create_venv
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.args import MODEL_DUMP_ARGS
from inspect_flow._util.path_util import absolute_path_relative_to

logger = getLogger(__name__)


def launch(
    spec: FlowSpec,
    base_dir: str,
    no_dotenv: bool = False,
    dry_run: bool = False,
    no_venv: bool = False,
) -> None:
    env = _get_env(base_dir, no_dotenv)

    if not spec.log_dir:
        raise ValueError("log_dir must be set before launching the flow spec")
    spec.log_dir = absolute_path_relative_to(spec.log_dir, base_dir=base_dir)

    if spec.options and spec.options.bundle_dir:
        # Ensure bundle_dir and bundle_url_mappings are absolute paths
        spec.options.bundle_dir = absolute_path_relative_to(
            spec.options.bundle_dir, base_dir=base_dir
        )
        if spec.options.bundle_url_mappings:
            spec.options.bundle_url_mappings = {
                absolute_path_relative_to(k, base_dir=base_dir): v
                for k, v in spec.options.bundle_url_mappings.items()
            }
    logger.info(f"Using log_dir: {spec.log_dir}")

    run_path = (Path(__file__).parents[1] / "_runner" / "run.py").absolute()
    base_dir = absolute_file_path(base_dir)
    run_args = ["--dry-run"] if dry_run else []
    args = ["--base-dir", base_dir] + run_args
    if spec.env:
        env.update(**spec.env)

    if no_venv:
        python_path = sys.executable
        file = _write_flow_yaml(spec, ".")
        try:
            subprocess.run(
                [str(python_path), str(run_path), "--file", file.as_posix(), *args],
                check=True,
                env=env,
            )
        finally:
            file.unlink(missing_ok=True)
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        # Set the virtual environment so that it will be created in the temp directory
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")

        create_venv(
            spec, base_dir=base_dir, temp_dir=temp_dir, env=env, dry_run=dry_run
        )

        python_path = Path(temp_dir) / ".venv" / "bin" / "python"
        file = _write_flow_yaml(spec, temp_dir)
        subprocess.run(
            [str(python_path), str(run_path), "--file", file.as_posix(), *args],
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


def _write_flow_yaml(spec: FlowSpec, dir: str) -> Path:
    flow_yaml_path = Path(dir) / "flow.yaml"
    with open(flow_yaml_path, "w") as f:
        yaml.dump(
            spec.model_dump(**MODEL_DUMP_ARGS),
            f,
            default_flow_style=False,
            sort_keys=False,
        )
    return flow_yaml_path
