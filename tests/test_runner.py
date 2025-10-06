from pathlib import Path

import pytest
from inspect_flow._runner.runner import run
from inspect_flow._types.types import EvalSetConfig, TaskGroupConfig


@pytest.mark.asyncio
async def test_run_environment() -> None:
    pyproject_toml_file = Path(__file__).parent.parent / "pyproject.toml"
    uv_lock_file = Path(__file__).parent.parent / "uv.lock"

    task_group = TaskGroupConfig(
        pyproject_toml_file=str(pyproject_toml_file),
        uv_lock_file=str(uv_lock_file),
        eval_set=EvalSetConfig(tasks=[]),
    )
    await run(task_group=task_group)
