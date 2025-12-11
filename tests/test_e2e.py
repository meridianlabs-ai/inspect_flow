import sys
from pathlib import Path

import yaml
from click.testing import CliRunner
from inspect_flow._api.api import load_job
from inspect_flow._cli.main import flow
from inspect_flow._types.flow_types import FlowSpec

from tests.test_helpers.log_helpers import init_test_logs, verify_test_logs


def test_local_e2e() -> None:
    log_dir = init_test_logs()

    config_path = Path(__file__).parent / "local_eval" / "flow" / "local_eval_flow.py"

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

    config = load_job(str(config_path))
    verify_test_logs(job=config, log_dir=log_dir)

    # Verify that the config file was written
    config_file = Path(log_dir) / "flow.yaml"
    assert config_file.exists()

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
    loaded_job = FlowSpec.model_validate(data, extra="forbid")
    # The python_version should match the current version
    assert (
        loaded_job.python_version
        == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
