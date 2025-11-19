import glob
import sys
from pathlib import Path

import yaml
from click.testing import CliRunner
from inspect_flow._cli.main import flow
from inspect_flow._config.load import load_config
from inspect_flow._types.flow_types import FlowJob

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

    # Verify that the config file was written with timestamp prefix
    config_files = glob.glob(f"{log_dir}/*_flow.yaml")
    assert len(config_files) == 1, f"Expected 1 config file, found {len(config_files)}"

    with open(config_files[0], "r") as f:
        data = yaml.safe_load(f)
    loaded_job = FlowJob.model_validate(data)
    # The python_version should match the current version
    assert (
        loaded_job.python_version
        == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
