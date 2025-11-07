from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from inspect_flow._cli.config import config_command
from inspect_flow._cli.run import run_command
from inspect_flow._types.flow_types import FConfig

CONFIG_FILE = "./examples/model_and_task_flow.py"


def test_run_command_overrides() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_launch,
        patch("inspect_flow._cli.run.load_config") as mock_config,
    ):
        # Mock the config object
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(
            run_command,
            [
                CONFIG_FILE,
                "--set",
                "dependencies=dep1",
                "--set",
                "defaults.solver.args.tool_calls=none",
            ],
            catch_exceptions=False,
        )

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_config was called with the correct file
        mock_config.assert_called_once_with(
            CONFIG_FILE,
            overrides=["dependencies=dep1", "defaults.solver.args.tool_calls=none"],
        )

        # Verify that launch was called with the config object and file path
        mock_launch.assert_called_once_with(mock_config_obj, CONFIG_FILE, [])


def test_config_command_overrides() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.config.load_config") as mock_config,
    ):
        mock_config.return_value = FConfig()

        result = runner.invoke(
            config_command,
            [
                CONFIG_FILE,
                "--set",
                "dependencies=dep1",
                "--set",
                "defaults.solver.args.tool_calls=none",
            ],
            catch_exceptions=False,
        )

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_config was called with the correct file
        mock_config.assert_called_once_with(
            CONFIG_FILE,
            overrides=["dependencies=dep1", "defaults.solver.args.tool_calls=none"],
        )


def test_run_command_dry_run() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_launch,
        patch("inspect_flow._cli.run.load_config") as mock_config,
    ):
        # Mock the config object
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        # Run the command with --dry-run flag
        result = runner.invoke(run_command, [CONFIG_FILE, "--dry-run"])

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_config was called with the correct file
        mock_config.assert_called_once_with(CONFIG_FILE, overrides=[])

        # Verify that launch was called with the config object and file path
        mock_launch.assert_called_once_with(mock_config_obj, CONFIG_FILE, ["--dry-run"])


def test_config_command_resolve() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.config.launch") as mock_launch,
        patch("inspect_flow._cli.config.load_config") as mock_config,
    ):
        # Mock the config object
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        # Run the command with --dry-run flag
        result = runner.invoke(config_command, [CONFIG_FILE, "--resolve"])

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_config was called with the correct file
        mock_config.assert_called_once_with(CONFIG_FILE, overrides=[])

        # Verify that launch was called with the config object and file path
        mock_launch.assert_called_once_with(mock_config_obj, CONFIG_FILE, ["--config"])
