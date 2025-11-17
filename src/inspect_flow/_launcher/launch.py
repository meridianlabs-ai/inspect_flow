import os
import pathlib
import subprocess
import sys
import tempfile
from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path

from inspect_flow._launcher.venv import create_venv
from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.path_util import set_cwd_env_var


def launch(
    config: FlowJob,
    run_args: list[str] | None = None,
) -> None:
    if not config.log_dir:
        raise ValueError("log_dir must be set before launching the flow job")

    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)
    set_cwd_env_var()
    config.log_dir = _resolve_log_dir(config, env=dict(os.environ))
    click.echo(f"Using log_dir: {config.log_dir}")

    with tempfile.TemporaryDirectory(dir=temp_dir_parent) as temp_dir:
        env = create_venv(config, temp_dir)
        if config.env:
            env.update(**config.env)

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


def _resolve_log_dir(config: FlowJob, env: dict[str, str]) -> str:
    assert config.log_dir
    absolute_log_dir = absolute_file_path(config.log_dir)
    if absolute_log_dir == config.log_dir:
        # Already an absolute path
        return absolute_log_dir

    # Resolve relative path based on config path if set
    if config_path := env.get("INSPECT_FLOW_CONFIG_PATH"):
        config_relative_path = Path(config_path).parent / config.log_dir
        return absolute_file_path(str(config_relative_path))

    # Resolve relative path based on cwd
    return absolute_log_dir
