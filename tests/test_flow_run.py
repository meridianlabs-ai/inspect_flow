import sys

import yaml
from click.testing import CliRunner
from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.run import flow_run
from inspect_flow._types.flow_types import FlowJob


def test_run_command_overrides() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("flow.yaml", "w") as f:
            f.write(config_to_yaml(FlowJob()))

        result = runner.invoke(
            flow_run,
            [
                "--file",
                "flow.yaml",
                "--dry-run",
            ],
            catch_exceptions=False,
        )

        # Check that the command executed successfully
        assert result.exit_code == 0
        data = yaml.safe_load(result.stdout)

        output_job = FlowJob.model_validate(data, extra="forbid")
        assert output_job == FlowJob(
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            tasks=[],
        )
