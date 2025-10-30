import os
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from inspect_flow._cli.submit import submit_command

CONFIG_FILE = "./examples/model_and_task_flow.py"


def test_submit_command_dry_run() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.submit.submit") as mock_submit,
        patch("inspect_flow._cli.submit.load_config") as mock_config,
    ):
        # Mock the config object
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        assert not os.environ.get("INSPECT_FLOW_DRY_RUN")

        # Run the command with --dry-run flag
        result = runner.invoke(submit_command, [CONFIG_FILE, "--dry-run"])

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that INSPECT_FLOW_DRY_RUN environment variable was set
        assert os.environ.get("INSPECT_FLOW_DRY_RUN") == "1"

        # Verify that load_config was called with the correct file
        mock_config.assert_called_once_with(CONFIG_FILE)

        # Verify that submit was called with the config object and file path
        mock_submit.assert_called_once_with(mock_config_obj, CONFIG_FILE)

        # Clean up environment variable
        if "INSPECT_FLOW_DRY_RUN" in os.environ:
            del os.environ["INSPECT_FLOW_DRY_RUN"]
