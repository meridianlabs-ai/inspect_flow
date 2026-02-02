import sys

import yaml
from click.testing import CliRunner
from inspect_flow._config.write import config_to_yaml
from inspect_flow._runner.run import flow_run
from inspect_flow._types.flow_types import FlowSpec


def test_run_command_overrides() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("flow.yaml", "w") as f:
            f.write(config_to_yaml(FlowSpec()))

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

        # Extract YAML content from between the Rich Rule decorations
        # Output format: \n─── Title ───\nyaml_content\n────────\n
        lines = result.stdout.strip().split("\n")
        yaml_lines = [
            line for line in lines if not line.startswith("─") and line.strip()
        ]
        yaml_content = "\n".join(yaml_lines)
        data = yaml.safe_load(yaml_content)

        output_spec = FlowSpec.model_validate(data, extra="forbid")
        assert output_spec == FlowSpec(
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            tasks=[],
        )
