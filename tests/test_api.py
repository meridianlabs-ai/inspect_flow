from unittest.mock import patch

from inspect_flow._types.flow_types import FlowJob
from inspect_flow.api import run

from tests.test_helpers.config_helpers import validate_config


def test_258_run_includes() -> None:
    job = FlowJob(includes=["defaults_flow.py"], tasks=["local_eval/noop"])
    with patch("inspect_flow._api.api.launch") as mock_launch:
        run(job=job, base_dir="./tests/config/")
    mock_launch.assert_called_once()
    launch_job = mock_launch.mock_calls[0].kwargs["job"]
    assert launch_job.includes is None
    validate_config(launch_job, "run_includes.yaml")
