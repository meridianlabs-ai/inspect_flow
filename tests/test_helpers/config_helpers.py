from pathlib import Path

import yaml
from deepdiff import DeepDiff
from inspect_flow import FlowJob
from pydantic_core import to_jsonable_python

update_examples = False


def write_flow_yaml(job: FlowJob, file_path: Path) -> None:
    job = FlowJob.model_validate(to_jsonable_python(job), extra="forbid")
    with open(file_path, "w") as f:
        yaml.dump(
            job.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_defaults=True,
                exclude_none=True,
            ),
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def validate_config(config: FlowJob, file_name: str) -> None:
    config = FlowJob.model_validate(to_jsonable_python(config), extra="forbid")
    # Load the example config file
    example_path = Path(__file__).parents[1] / "expected" / file_name
    if not example_path.exists() and update_examples:
        expected_config = {}
    else:
        with open(example_path, "r") as f:
            expected_config = yaml.safe_load(f)

    # Compare the generated config with the example
    generated_config = config.model_dump(
        mode="json", exclude_unset=True, exclude_defaults=True, exclude_none=True
    )
    if update_examples and generated_config != expected_config:
        write_flow_yaml(config, example_path)
    else:
        if generated_config != expected_config:
            diff = DeepDiff(expected_config, generated_config, verbose_level=2)
            error_msg = (
                f"\nConfig mismatch for: {file_name}\n"
                f"Expected file: {example_path}\n\n"
                f"Differences:\n{diff.pretty()}"
            )
            raise AssertionError(error_msg)
