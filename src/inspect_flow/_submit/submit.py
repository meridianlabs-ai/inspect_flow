import pathlib
import subprocess
import sys
import tempfile
from pathlib import Path

from inspect_ai._util.file import absolute_file_path
from pydantic_core import to_jsonable_python

from inspect_flow._submit.venv import create_venv
from inspect_flow._types.flow_types import FConfig
from inspect_flow._types.generated import FlowConfig
from inspect_flow._util.path_util import set_path_env_vars


def submit(
    config: FConfig | FlowConfig,
    config_file_path: str | None = None,
    run_args: list[str] | None = None,
) -> None:
    if not isinstance(config, FConfig):
        config = FConfig.model_validate(to_jsonable_python(config))

    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)

    config.flow_dir = absolute_file_path(config.flow_dir or "logs/flow")

    with tempfile.TemporaryDirectory(dir=temp_dir_parent) as temp_dir:
        env = create_venv(config, temp_dir)
        if config.env:
            env.update(**config.env)
        set_path_env_vars(env, config_file_path)

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
