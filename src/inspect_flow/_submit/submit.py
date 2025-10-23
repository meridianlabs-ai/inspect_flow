import pathlib
import subprocess
import tempfile
from pathlib import Path

from inspect_flow._submit.venv import create_venv
from inspect_flow._types.flow_types import FlowConfig


def submit(config: FlowConfig):
    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)

    config.log_dir = str(Path(config.log_dir).resolve())

    with tempfile.TemporaryDirectory(dir=temp_dir_parent) as temp_dir:
        env = create_venv(config, temp_dir)

        run_path = (Path(__file__).parents[1] / "_runner" / "run.py").absolute()
        subprocess.run(
            ["uv", "run", str(run_path)],
            cwd=temp_dir,
            check=True,
            env=env,
        )
