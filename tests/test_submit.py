import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_flow import flow_config
from inspect_flow._submit.submit import submit


def test_submit() -> None:
    with patch("subprocess.run") as mock_run:
        submit(config=flow_config({"tasks": ["task_name"]}))

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


def test_submit_handles_subprocess_error() -> None:
    """Test that CalledProcessError causes sys.exit without stack trace."""
    with (
        patch("subprocess.run") as mock_run,
        pytest.raises(SystemExit) as exc_info,
    ):
        # Configure the third subprocess.run call to raise CalledProcessError
        mock_run.side_effect = [
            None,  # First call succeeds
            None,  # Second call succeeds
            subprocess.CalledProcessError(42, "cmd"),  # Third call fails
        ]

        submit(config=flow_config({"tasks": ["task_name"]}))

    # Verify sys.exit was called with the subprocess's return code
    assert exc_info.value.code == 42


def test_env() -> None:
    """Test that CalledProcessError causes sys.exit without stack trace."""
    with patch("subprocess.run") as mock_run:
        submit(
            config=flow_config(
                {
                    "tasks": ["task_name"],
                    "env": {"myenv1": "value1", "myenv2": "value2"},
                }
            )
        )

    assert mock_run.call_count == 3
    env = mock_run.mock_calls[2].kwargs["env"]
    assert env["myenv1"] == "value1"
    assert env["myenv2"] == "value2"
