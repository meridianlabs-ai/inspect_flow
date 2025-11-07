from pathlib import Path

from inspect_flow._config.config import load_config
from inspect_flow._launcher.launch import launch

from tests.test_helpers.log_helpers import init_test_logs, verify_test_logs


def test_local_e2e() -> None:
    log_dir = init_test_logs()

    config_path = Path(__file__).parent / "config" / "e2e_test_flow.py"
    config = load_config(str(config_path))

    launch(config=config, config_file_path=str(config_path))

    verify_test_logs(config=config, log_dir=log_dir)
