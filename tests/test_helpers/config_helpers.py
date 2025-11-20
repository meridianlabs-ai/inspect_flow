from pathlib import Path

import yaml
from inspect_flow import FlowJob
from pydantic_core import to_jsonable_python

update_examples = False


def write_flow_yaml(job: FlowJob, file_path: Path) -> None:
    job = FlowJob.model_validate(to_jsonable_python(job))
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
    config = FlowJob.model_validate(to_jsonable_python(config))
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
        assert generated_config == expected_config
