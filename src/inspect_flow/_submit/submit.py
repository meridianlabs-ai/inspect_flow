import pathlib
import subprocess
import tempfile
from pathlib import Path

from inspect_flow._submit.venv import create_venv
from inspect_flow._types.types import Config, TaskGroupConfig


def run(task_group: TaskGroupConfig) -> None:
    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)

    # TODO:ransom - make log dir configurable
    task_group.eval_set.log_dir = str(Path.cwd() / "logs" / task_group.eval_set.log_dir)

    with tempfile.TemporaryDirectory(dir=temp_dir_parent) as temp_dir:
        env = create_venv(task_group, temp_dir)

        run_path = (Path(__file__).parent.parent / "_runner" / "run.py").absolute()
        subprocess.run(
            ["uv", "run", str(run_path)],
            cwd=temp_dir,
            check=True,
            env=env,
        )


def submit(config: Config):
    for task_group in config.run.task_groups:
        run(task_group=task_group)
