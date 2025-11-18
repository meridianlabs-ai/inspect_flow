from pathlib import Path

from click.testing import CliRunner
from inspect_flow._cli.main import flow
from inspect_flow._config.load import load_config

from tests.test_helpers.log_helpers import init_test_logs, verify_test_logs


def test_local_e2e() -> None:
    log_dir = init_test_logs()

    config_path = Path(__file__).parent / "config" / "e2e_test_flow.py"

    runner = CliRunner()

    result = runner.invoke(
        flow,
        [
            "run",
            str(config_path),
            "--log-dir",
            log_dir,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    config = load_config(str(config_path))
    verify_test_logs(config=config, log_dir=log_dir)
