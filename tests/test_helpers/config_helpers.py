from pathlib import Path

import yaml
from deepdiff import DeepDiff
from inspect_flow import FlowSpec
from inspect_flow._util.args import MODEL_DUMP_ARGS

update_examples = False


def write_flow_yaml(job: FlowSpec, file_path: Path) -> None:
    with open(file_path, "w") as f:
        yaml.dump(
            job.model_dump(**MODEL_DUMP_ARGS),
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def validate_config(job: FlowSpec, file_name: str) -> None:
    # Load the example config file
    example_path = Path(__file__).parents[1] / "expected" / file_name
    if not example_path.exists() and update_examples:
        expected_config = {}
    else:
        with open(example_path, "r") as f:
            expected_config = yaml.safe_load(f)

    # Compare the generated config with the example
    generated_config = job.model_dump(**MODEL_DUMP_ARGS)
    if update_examples and generated_config != expected_config:
        write_flow_yaml(job, example_path)
    else:
        if generated_config != expected_config:
            diff = DeepDiff(expected_config, generated_config, verbose_level=2)
            error_msg = (
                f"\nConfig mismatch for: {file_name}\n"
                f"Expected file: {example_path}\n\n"
                f"Differences:\n{diff.pretty()}"
            )
            raise AssertionError(error_msg)
