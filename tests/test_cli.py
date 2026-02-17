from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from inspect_flow._cli.config import config_command
from inspect_flow._cli.main import flow
from inspect_flow._cli.options import _options_to_overrides
from inspect_flow._cli.run import run_command
from inspect_flow._cli.store import store_command
from inspect_flow._config.load import ConfigOptions
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._version import __version__

CONFIG_FILE = "./tests/config/model_and_task_flow.py"
CONFIG_FILE_RESOLVED = Path(CONFIG_FILE).resolve().as_posix()
CONFIG_FILE_DIR = Path(CONFIG_FILE).parent.resolve().as_posix()

COMMON_DEFAULTS = {
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
                "--store",
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
                    "store=s3://my-bucket/flow-db",
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


def test_run_command_venv() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(run_command, [CONFIG_FILE, "--venv"])

        assert result.exit_code == 0

        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED,
            options=ConfigOptions(
                overrides=["execution_type=venv"],
            ),
        )

        mock_run.assert_called_once_with(
            mock_config_obj,
            **COMMON_DEFAULTS,
            base_dir=CONFIG_FILE_DIR,
        )


def test_run_command_allow_dirty() -> None:
    runner = CliRunner()
    with (
        patch("inspect_flow._cli.run.launch") as mock_run,
        patch("inspect_flow._cli.run.int_load_spec") as mock_config,
    ):
        mock_config_obj = MagicMock()
        mock_config.return_value = mock_config_obj

        result = runner.invoke(run_command, [CONFIG_FILE, "--log-dir-allow-dirty"])

        assert result.exit_code == 0

        # Verify that load_spec was called with the correct file
        mock_config.assert_called_once_with(
            CONFIG_FILE_RESOLVED,
            options=ConfigOptions(
                overrides=[
                    "options.log_dir_allow_dirty=True",
                ],
                args={},
            ),
        )

        mock_run.assert_called_once_with(
            mock_config_obj,
            **(COMMON_DEFAULTS),
            base_dir=CONFIG_FILE_DIR,
        )


def test_options_to_overrides() -> None:
    overrides = _options_to_overrides(
        log_dir="option_dir",
        limit=1,
        set=["log_dir=set_dir", "options.limit=5"],
        log_dir_allow_dirty=True,
    )

    assert len(overrides) == 5
    assert overrides == [
        "log_dir=set_dir",
        "options.limit=5",
        "log_dir=" + Path("option_dir").resolve().as_posix(),
        "options.limit=1",
        "options.log_dir_allow_dirty=True",
    ]


def test_inspect_object_overrides() -> None:
    runner = CliRunner()

    result = runner.invoke(
        config_command,
        [
            "./tests/config/inspect_objects_flow.py",
            "--set",
            "defaults.solver.args.tool_calls=none",
        ],
        catch_exceptions=False,
    )

    # Check that the command executed successfully
    assert result.exit_code == 0


def test_417_invalid_run() -> None:
    runner = CliRunner()

    result = runner.invoke(
        run_command,
        [
            "./tests/config/invalid_run_flow.py",
        ],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert "run() cannot be called from within a flow spec file" in str(
        result.exception
    )


def test_store_commands() -> None:
    log_dir = "tests/test_logs/logs1"
    runner = CliRunner()
    result = runner.invoke(store_command, ["import", log_dir, "--log-level", "error"])
    assert result.exit_code == 0
    result = runner.invoke(store_command, ["list", "--log-level", "error"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert (
        lines[-2]
        == log_dir
        + "/2025-12-11T18-00-43+00-00_gpqa-diamond_NL3aygdanSgqAJfzoMFuH6.eval"
    )
    assert (
        lines[-1]
        == log_dir
        + "/2026-01-09T18-27-59+00-00_gpqa-diamond_nbjF337MtumE8dao4wZ3vj.eval"
    )


def test_store_info() -> None:
    log_dir = "tests/test_logs/logs1"
    runner = CliRunner()
    runner.invoke(store_command, ["import", log_dir, "--log-level", "error"])
    result = runner.invoke(store_command, ["info", "--log-level", "error"])
    assert result.exit_code == 0
    assert "2 logs" in result.output
    assert "1 log dir" in result.output
    assert "0.2.0" in result.output


def test_store_info_empty() -> None:
    runner = CliRunner()
    result = runner.invoke(store_command, ["info", "--log-level", "error"])
    assert result.exit_code == 0
    assert "Store not found" in result.output


def test_store_delete() -> None:
    log_dir = "tests/test_logs/logs1"
    runner = CliRunner()
    runner.invoke(store_command, ["import", log_dir, "--log-level", "error"])
    result = runner.invoke(
        store_command, ["delete", "--log-level", "error"], input="y\n"
    )
    assert result.exit_code == 0
    assert "Deleted store" in result.output
    result = runner.invoke(store_command, ["info", "--log-level", "error"])
    assert "Store not found" in result.output


def test_store_delete_yes_flag() -> None:
    log_dir = "tests/test_logs/logs1"
    runner = CliRunner()
    runner.invoke(store_command, ["import", log_dir, "--log-level", "error"])
    result = runner.invoke(store_command, ["delete", "--yes", "--log-level", "error"])
    assert result.exit_code == 0
    assert "Deleted store" in result.output


def test_store_delete_abort() -> None:
    log_dir = "tests/test_logs/logs1"
    runner = CliRunner()
    runner.invoke(store_command, ["import", log_dir, "--log-level", "error"])
    result = runner.invoke(
        store_command, ["delete", "--log-level", "error"], input="n\n"
    )
    assert result.exit_code != 0
    result = runner.invoke(store_command, ["info", "--log-level", "error"])
    assert "2 logs" in result.output


def test_store_delete_not_found() -> None:
    runner = CliRunner()
    result = runner.invoke(store_command, ["delete", "--log-level", "error"])
    assert result.exit_code == 0
    assert "Store not found" in result.output


def test_store_list_format_flat() -> None:
    log_dir = "tests/test_logs/logs1"
    runner = CliRunner()
    runner.invoke(store_command, ["import", log_dir, "--log-level", "error"])
    result = runner.invoke(
        store_command, ["list", "--format", "flat", "--log-level", "error"]
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert (
        lines[-2]
        == log_dir
        + "/2025-12-11T18-00-43+00-00_gpqa-diamond_NL3aygdanSgqAJfzoMFuH6.eval"
    )


def test_store_list_format_tree() -> None:
    log_dir = "tests/test_logs/logs1"
    runner = CliRunner()
    runner.invoke(store_command, ["import", log_dir, "--log-level", "error"])
    result = runner.invoke(
        store_command, ["list", "--format", "tree", "--log-level", "error"]
    )
    assert result.exit_code == 0
    assert "logs1" in result.output
    assert "gpqa-diamond" in result.output


def test_run_display_passed_to_eval_set(mock_eval_set: MagicMock) -> None:
    runner = CliRunner()
    result = runner.invoke(
        run_command,
        [CONFIG_FILE, "--display", "rich", "--log-dir-allow-dirty"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    mock_eval_set.assert_called_once()
    assert mock_eval_set.call_args.kwargs["display"] == "rich"
