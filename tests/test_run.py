import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from inspect_ai import Task
from inspect_flow._runner.run import run_eval_set
from inspect_flow._types.types import EvalSetConfig, PackageConfig, TaskConfig


def test_task_with_get_model() -> None:
    # TODO:ransom would prefer not to install as part of tests. Maybe reference local files to get tasks instead of using a package?
    # Install local_eval package
    local_eval_path = Path(__file__).parent.parent / "examples" / "local_eval"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(local_eval_path)], check=True
    )

    with patch("inspect_ai.eval_set") as mock_eval_set:
        run_eval_set(
            eval_set_config=EvalSetConfig(
                tasks=[
                    PackageConfig(
                        name="local_eval",
                        package="local_eval",
                        items=[TaskConfig(name="task_with_get_model")],
                    )
                ],
                log_dir="get_model",
            )
        )

        # Verify eval_set was called once
        mock_eval_set.assert_called_once()

        # Get the call arguments
        call_args = mock_eval_set.call_args

        # Verify the first positional argument is a single Task object
        tasks_arg = call_args.kwargs["tasks"]
        assert len(tasks_arg) == 1
        assert isinstance(tasks_arg[0], Task)
