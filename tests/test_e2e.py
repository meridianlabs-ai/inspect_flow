from pathlib import Path

from inspect_flow._config.config import load_config
from inspect_flow._submit.submit import submit
from inspect_flow._types.flow_types import flow_config

from tests.test_helpers.log_helpers import init_test_logs, verify_test_logs


def test_local_e2e() -> None:
    log_dir = init_test_logs()

    config_path = Path(__file__).parents[1] / "examples" / "e2e_test_flow.yaml"
    config = load_config(str(config_path))

    submit(config=config)

    verify_test_logs(config=config, log_dir=log_dir)


def test_relative_py_file() -> None:
    log_dir = init_test_logs()

    config_path = Path(__file__).parents[1] / "examples" / "relative_py_file.py"
    config = load_config(str(config_path))

    submit(config=config, config_file_path=str(config_path))

    verify_test_logs(config=config, log_dir=log_dir)


def test_cwd_relative_py_file() -> None:
    log_dir = init_test_logs()

    config = flow_config(
        {
            "log_dir": "logs/local_logs",
            "eval_set_options": {"limit": 1},
            "matrix": [
                {
                    "tasks": [
                        {
                            "name": "noop",
                            "file": "examples/local_eval/src/local_eval/noop.py",
                        }
                    ],
                    "models": ["mockllm/mock-llm"],
                },
            ],
        }
    )

    submit(config=config)

    verify_test_logs(config=config, log_dir=log_dir)
