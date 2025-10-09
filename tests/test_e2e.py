import os
import shutil
from pathlib import Path

from inspect_flow._client.client import Client
from inspect_flow._config.config import load_config
from inspect_flow._runner.run import run_eval_set


def test_local_e2e() -> None:
    os.chdir(Path(__file__).parent.parent)

    # Remove logs/local_logs directory if it exists
    logs_dir = Path.cwd() / "logs" / "local_logs"
    if logs_dir.exists():
        shutil.rmtree(logs_dir)

    config_path = Path.cwd() / "examples" / "local.eval-set.yaml"

    client = Client()
    client.submit(str(config_path))

    # Check that logs/local_logs directory was created
    assert logs_dir.exists()
