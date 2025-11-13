import os
import pathlib
import subprocess
import sys
import tempfile
from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from pydantic_core import to_jsonable_python

from inspect_flow._launcher.venv import create_venv
from inspect_flow._types.flow_types import FConfig
from inspect_flow._types.generated import FlowConfig
from inspect_flow._util.path_util import set_cwd_env_var


def launch(
    config: FConfig | FlowConfig,
    run_args: list[str] | None = None,
) -> None:
    if not isinstance(config, FConfig):
        config = FConfig.model_validate(to_jsonable_python(config))

    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)
    set_cwd_env_var()
    config.flow_dir = _resolve_flow_dir(config, env=dict(os.environ))
    click.echo(f"Using flow_dir: {config.flow_dir}")

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


def _resolve_flow_dir(config: FConfig, env: dict[str, str]) -> str:
    if config.flow_dir:
        flow_dir = config.flow_dir
    elif "INSPECT_FLOW_DIR" in env:
        flow_dir = env["INSPECT_FLOW_DIR"]
    elif "INSPECT_LOG_DIR" in env:
        flow_dir = env["INSPECT_LOG_DIR"] + "/flow"
    else:
        flow_dir = "logs/flow"
    return absolute_file_path(flow_dir)
