from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from inspect_flow._cli.config import config_command
from inspect_flow._cli.main import flow
from inspect_flow._cli.options import _options_to_overrides
from inspect_flow._cli.run import run_command
from inspect_flow._config.load import ConfigOptions
from inspect_flow._types.flow_types import FlowJob
from inspect_flow._version import __version__

CONFIG_FILE = "./tests/config/model_and_task_flow.py"


def test_flow_help() -> None:
    runner = CliRunner()
    result = runner.invoke(
        flow,
        [],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output.startswith("Usage:")


def test_flow_version() -> None:
    runner = CliRunner()
    result = runner.invoke(
        flow,
        ["--version"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == __version__ + "\n"


def test_run_command_overrides() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.run") as mock_run,
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
            config_options=ConfigOptions(
                overrides=["dependencies=dep1", "defaults.solver.args.tool_calls=none"]
            ),
        )

        # Verify that run was called with the config object and file path
        mock_run.assert_called_once_with(mock_config_obj, dry_run=False)


def test_config_command_overrides() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.config.load_config") as mock_config,
    ):
        mock_config.return_value = FlowJob()

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
            config_options=ConfigOptions(
                overrides=["dependencies=dep1", "defaults.solver.args.tool_calls=none"]
            ),
        )


def test_run_command_dry_run() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.run") as mock_run,
        patch("inspect_flow._cli.run.load_config") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(run_command, [CONFIG_FILE, "--dry-run"])

        assert result.exit_code == 0

        mock_config.assert_called_once_with(CONFIG_FILE, config_options=ConfigOptions())

        mock_run.assert_called_once_with(mock_config_obj, dry_run=True)


def test_run_command_flow_vars() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.run") as mock_run,
        patch("inspect_flow._cli.run.load_config") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(
            run_command, [CONFIG_FILE, "--var", "var1=value1", "--var", "var2=value2"]
        )

        assert result.exit_code == 0

        mock_config.assert_called_once_with(
            CONFIG_FILE,
            config_options=ConfigOptions(
                flow_vars={"var1": "value1", "var2": "value2"}
            ),
        )

        mock_run.assert_called_once_with(mock_config_obj, dry_run=False)


def test_config_command_resolve() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.config.config") as mock_config,
        patch("inspect_flow._cli.config.load_config") as mock_load,
    ):
        mock_config_obj = MagicMock()
        mock_load.return_value = mock_config_obj

        result = runner.invoke(config_command, [CONFIG_FILE, "--resolve"])

        assert result.exit_code == 0

        mock_load.assert_called_once_with(CONFIG_FILE, config_options=ConfigOptions())

        mock_config.assert_called_once_with(mock_config_obj, resolve=True)


def test_options_to_overrides() -> None:
    overrides = _options_to_overrides(
        log_dir="option_dir",
        limit=1,
        set=["log_dir=set_dir", "options.limit=5", "options.log_dir_allow_dirty=True"],
    )

    assert len(overrides) == 5
    assert overrides == [
        "log_dir=set_dir",
        "options.limit=5",
        "options.log_dir_allow_dirty=True",
        "log_dir=option_dir",
        "options.limit=1",
    ]
