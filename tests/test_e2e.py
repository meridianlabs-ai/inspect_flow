import os
import shutil
from itertools import product
from pathlib import Path

from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_flow._client.client import Client


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
    log_list = list_eval_logs(str(logs_dir))

    assert len(log_list) == 4
    logs = [read_eval_log(log) for log in log_list]
    assert all(log.status == "success" for log in logs), (
        "All logs should have status 'success'"
    )
    assert sorted([(log.eval.task, log.eval.model) for log in logs]) == sorted(
        product(
            ("local_eval/noop", "local_eval/noop2"),
            ("mockllm/mock-llm1", "mockllm/mock-llm2"),
        )
    ), "Logs should cover all task/model combinations"
