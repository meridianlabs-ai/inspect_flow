from pathlib import Path
from unittest.mock import patch

from inspect_flow._submit.submit import submit
from inspect_flow._types.flow_types import FlowConfig


def test_submit() -> None:
    with patch("subprocess.run") as mock_run:
        submit(config=FlowConfig(matrix=[{"tasks": ["task_name"]}]))

        assert mock_run.call_count == 3
        args = mock_run.mock_calls[2].args[0]
        assert len(args) == 2
        assert str(args[0]).endswith("/.venv/bin/python")
        assert args[1] == str(
            (
                Path(__file__).parents[1]
                / "src"
                / "inspect_flow"
                / "_runner"
                / "run.py"
            ).resolve()
        )
