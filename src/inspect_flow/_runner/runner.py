import json
import os
import pathlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from inspect_flow._types.types import TaskGroupConfig


def run(task_group: TaskGroupConfig) -> None:
    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_dir_parent) as temp_dir:
        # update log_dirs to be inside logs directory
        # TODO:ransom - make log dir configurable
        task_group.eval_set.log_dir = str(
            Path.cwd() / "logs" / task_group.eval_set.log_dir
        )
        # Serialize task_group to JSON and write to file
        task_group_json_path = Path(temp_dir) / "task_group.json"
        with open(task_group_json_path, "w") as f:
            json.dump(task_group.model_dump(), f, indent=2)

        if task_group.pyproject_toml_file:
            shutil.copy2(
                Path(task_group.pyproject_toml_file), Path(temp_dir) / "pyproject.toml"
            )
        if task_group.uv_lock_file:
            shutil.copy2(Path(task_group.uv_lock_file), Path(temp_dir) / "uv.lock")

        # Remove VIRTUAL_ENV from environment to avoid virtual environment confusion
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)

        subprocess.run(
            [
                "uv",
                "venv",
            ],
            cwd=temp_dir,
            check=True,
            env=env,
        )

        inspect_flow_path = Path(__file__).parent.parent.parent.parent

        eval_set_config = task_group.eval_set
        package_configs = [*eval_set_config.tasks, *(eval_set_config.models or [])]
        dependencies: List[str] = [
            *(package_config.package for package_config in package_configs),
            str(inspect_flow_path),
        ]
        dependencies = [
            dep if not dep.startswith("./") else str(Path(dep).resolve())
            for dep in dependencies
        ]

        subprocess.run(
            ["uv", "pip", "install", *sorted(dependencies)],
            cwd=temp_dir,
            check=True,
            env=env,
        )

        run_path = Path(__file__).parent / "run.py"
        subprocess.run(
            ["uv", "run", "--no-project", str(run_path)],
            cwd=temp_dir,
            check=True,
            env=env,
        )
