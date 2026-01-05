import sys
from pathlib import Path

import yaml
from click.testing import CliRunner
from inspect_flow._api.api import load_spec
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

    # #334 Verify warning about duplicate dependency files
    assert (
        "Multiple dependency files found when auto-detecting dependencies. Using 'pyproject.toml'"
        in result.stdout
    )
    # requirements.txt ignored in same directory as pyproject.toml
    assert "and ignoring 'requirements.txt'" in result.stdout
    # pyproject.toml ignored in parent directory
    assert "and ignoring 'pyproject.toml'" in result.stdout

    config = load_spec(str(config_path))
    verify_test_logs(spec=config, log_dir=log_dir)

    # Verify that the config file was written
    config_file = Path(log_dir) / "flow.yaml"
    assert config_file.exists()

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)
    loaded_spec = FlowSpec.model_validate(data, extra="forbid")
    # The uv.lock specifies python version >= 3.12
    if sys.version_info >= (3, 12):
        assert (
            loaded_spec.python_version
            == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
    else:
        assert loaded_spec.python_version == "3.13.9"  # most recent version
