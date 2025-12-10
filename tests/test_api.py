from unittest.mock import patch

from inspect_flow._types.flow_types import FlowJob, FlowTask, not_given
from inspect_flow.api import config, run

from tests.test_helpers.config_helpers import validate_config


def test_258_run_includes() -> None:
    job = FlowJob(
        includes=["defaults_flow.py"],
        tasks=[
            "local_eval/noop",
            FlowTask(name="local_eval/noop", model="{defaults[model][name]}"),
        ],
    )
    with patch("inspect_flow._api.api.launch") as mock_launch:
        run(job=job, base_dir="./tests/config/")
    mock_launch.assert_called_once()
    launch_job = mock_launch.mock_calls[0].kwargs["job"]
    assert launch_job.includes == not_given
    validate_config(launch_job, "run_includes.yaml")


def test_config() -> None:
    job = FlowJob(
        tasks=[
            "local_eval/noop",
        ],
    )
    dump = config(job=job, base_dir="./tests/config/")
    expected_dump = """tasks:
- name: local_eval/noop
"""
    assert dump == expected_dump
