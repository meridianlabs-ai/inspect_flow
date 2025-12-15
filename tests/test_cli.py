from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from inspect_flow._cli.config import config_command
from inspect_flow._cli.main import flow
from inspect_flow._cli.options import _options_to_overrides
from inspect_flow._cli.run import run_command
from inspect_flow._config.load import ConfigOptions
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._version import __version__

CONFIG_FILE = "./tests/config/model_and_task_flow.py"
CONFIG_FILE_RESOLVED = Path(CONFIG_FILE).resolve().as_posix()
CONFIG_FILE_DIR = Path(CONFIG_FILE).parent.resolve().as_posix()

COMMON_DEFAULTS = {
    "no_venv": False,
    "no_dotenv": False,
    "dry_run": False,
}


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
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        # Mock the config object
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(
            run_command,
            [
                CONFIG_FILE,
                "--set",
                "dependencies.additional_dependencies=dep1",
                "--set",
                "defaults.solver.args.tool_calls=none",
                "--log-dir",
                "s3://my-bucket/flow-logs",
                "--database",
                "s3://my-bucket/flow-db",
            ],
            catch_exceptions=False,
        )

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_spec was called with the correct file
        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED,
            options=ConfigOptions(
                overrides=[
                    "dependencies.additional_dependencies=dep1",
                    "defaults.solver.args.tool_calls=none",
                    "database=s3://my-bucket/flow-db",
                    "log_dir=s3://my-bucket/flow-logs",
                ],
                args={},
            ),
        )

        # Verify that run was called with the config object and file path
        mock_run.assert_called_once_with(
            mock_config_obj, **COMMON_DEFAULTS, base_dir=CONFIG_FILE_DIR
        )


def test_run_command_log_dir_create_unique() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        # Mock the config object
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(
            run_command,
            [
                CONFIG_FILE,
                "--log-dir-create-unique",
            ],
            catch_exceptions=False,
        )

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_spec was called with the correct file
        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED,
            options=ConfigOptions(
                overrides=["log_dir_create_unique=True"],
                args={},
            ),
        )

        # Verify that run was called with the config object and file path
        mock_run.assert_called_once_with(
            mock_config_obj,
            **COMMON_DEFAULTS,
            base_dir=CONFIG_FILE_DIR,
        )


def test_config_command_overrides() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.config.int_load_spec") as mock_config,
    ):
        mock_config.return_value = FlowSpec()

        result = runner.invoke(
            config_command,
            [
                CONFIG_FILE,
                "--set",
                "dependencies.additional_dependencies=dep1",
                "--set",
                "defaults.solver.args.tool_calls=none",
            ],
            catch_exceptions=False,
        )

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_spec was called with the correct file
        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED,
            options=ConfigOptions(
                overrides=[
                    "dependencies.additional_dependencies=dep1",
                    "defaults.solver.args.tool_calls=none",
                ],
                args={},
            ),
        )


def test_config_command_overrides_envvars(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    monkeypatch.setenv(
        "INSPECT_FLOW_SET",
        "dependencies.additional_dependencies=dep1 defaults.solver.args.tool_calls=none",
    )
    with (
        patch("inspect_flow._cli.config.int_load_spec") as mock_config,
    ):
        mock_config.return_value = FlowSpec()

        result = runner.invoke(
            config_command,
            [CONFIG_FILE],
            catch_exceptions=False,
        )

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify that load_spec was called with the correct file
        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED,
            options=ConfigOptions(
                overrides=[
                    "dependencies.additional_dependencies=dep1",
                    "defaults.solver.args.tool_calls=none",
                ],
                args={},
            ),
        )


def test_run_command_dry_run() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(run_command, [CONFIG_FILE, "--dry-run"])

        assert result.exit_code == 0

        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED, options=ConfigOptions(args={}, overrides=[])
        )

        mock_run.assert_called_once_with(
            mock_config_obj,
            **(COMMON_DEFAULTS | {"dry_run": True}),
            base_dir=CONFIG_FILE_DIR,
        )


def test_run_command_args() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(
            run_command, [CONFIG_FILE, "--arg", "var1=value1", "--arg", "var2=value2"]
        )

        assert result.exit_code == 0

        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED,
            options=ConfigOptions(
                args={"var1": "value1", "var2": "value2"},
                overrides=[],
            ),
        )

        mock_run.assert_called_once_with(
            mock_config_obj,
            **COMMON_DEFAULTS,
            base_dir=CONFIG_FILE_DIR,
        )


def test_run_command_no_venv() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(run_command, [CONFIG_FILE, "--no-venv"])

        assert result.exit_code == 0

        mock_config.assert_called_once()

        mock_run.assert_called_once_with(
            mock_config_obj,
            **(COMMON_DEFAULTS | {"no_venv": True}),
            base_dir=CONFIG_FILE_DIR,
        )


def test_run_command_log_level() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.init_flow_logging") as mock_init_flow_logging,
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(run_command, [CONFIG_FILE, "--log-level", "warning"])

        assert result.exit_code == 0

        mock_init_flow_logging.assert_called_once_with("warning")

        mock_config.assert_called_once()

        mock_run.assert_called_once()


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
