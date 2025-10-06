import os
import pathlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from inspect_flow._types.types import TaskGroupConfig


async def run(task_group: TaskGroupConfig) -> None:
    temp_dir_parent: pathlib.Path = pathlib.Path.home() / ".cache" / "inspect-flow"
    temp_dir_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_dir_parent, delete=False) as temp_dir:
        shutil.copy2(
            Path(task_group.pyproject_toml_file), Path(temp_dir) / "pyproject.toml"
        )
        if task_group.uv_lock_file:
            shutil.copy2(Path(task_group.uv_lock_file), Path(temp_dir) / "uv.lock")

        # subprocess.run(
        #     ["uv", "venv"],
        #     cwd=temp_dir,
        #     check=True,
        #     capture_output=True,
        #     text=True,
        #     env=os.environ.copy(),
        # )

        subprocess.run(
            ["uv", "sync", "--no-install-project"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        eval_set_config = task_group.eval_set
        package_configs = [*eval_set_config.tasks, *(eval_set_config.models or [])]
        dependencies = {*(package_config.package for package_config in package_configs)}

        subprocess.run(
            ["uv", "pip", "install", *sorted(dependencies)],
            cwd=temp_dir,
            check=True,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
