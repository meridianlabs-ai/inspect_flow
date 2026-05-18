import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_flow._api.api import load_spec
from inspect_flow._cli.main import flow
from inspect_flow._types.flow_types import FlowInternal, FlowSpec

from tests.test_helpers.log_helpers import init_test_logs, verify_test_logs


@pytest.mark.slow
def test_local_e2e() -> None:
    log_dir = init_test_logs()

    config_path = Path(__file__).parent / "local_eval" / "flow" / "local_eval_flow.py"

    runner = CliRunner()

    result = runner.invoke(
        flow,
        ["run", str(config_path), "--log-dir", log_dir, "--venv"],
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
    assert (
        loaded_spec.python_version
        == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    # The config registers an @after_instantiate hook that tags each task.
    # Asserting the tag appears on every produced log proves the venv child
    # loaded the bridge file, re-registered the decorator, and ran the hook.
    assert isinstance(loaded_spec.internal, FlowInternal)
    files = loaded_spec.internal.python_files
    assert isinstance(files, list)
    assert any(f.endswith("local_eval_flow.py") for f in files)

    logs = [read_eval_log(log) for log in list_eval_logs(log_dir)]
    assert logs
    for log in logs:
        assert "e2e_hook_ran" in (log.eval.tags or []), (
            f"hook tag missing from {log.location}; tags={log.eval.tags}"
        )
