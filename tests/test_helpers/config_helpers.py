from pathlib import Path
from typing import Any

import yaml
from deepdiff import DeepDiff
from inspect_flow import FlowSpec
from inspect_flow._util.pydantic_util import model_dump

update_examples = False

# The parent of the project root - used to strip absolute paths from configs
_PROJECT_ROOT_PARENT = str(Path(__file__).parents[3]) + "/"


def _strip_absolute_paths(value: Any) -> Any:
    """Recursively strip absolute paths from the config.

    Replaces absolute paths that start with the project root parent directory
    with relative paths starting from 'inspect_flow/'.
    """
    if isinstance(value, str):
        if value.startswith(_PROJECT_ROOT_PARENT):
            return value[len(_PROJECT_ROOT_PARENT) :]
        return value
    elif isinstance(value, dict):
        return {k: _strip_absolute_paths(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_strip_absolute_paths(item) for item in value]
    else:
        return value


def write_flow_yaml(spec: FlowSpec, file_path: Path) -> None:
    with open(file_path, "w") as f:
        yaml.dump(
            _strip_absolute_paths(model_dump(spec)),
            f,
            default_flow_style=False,
            sort_keys=False,
        )


def validate_config(spec: FlowSpec, file_name: str) -> None:
    # Load the example config file
    example_path = Path(__file__).parents[1] / "expected" / file_name
    if not example_path.exists() and update_examples:
        expected_config = {}
    else:
        with open(example_path, "r") as f:
            expected_config = yaml.safe_load(f)

    # Compare the generated config with the example
    generated_config = _strip_absolute_paths(model_dump(spec))
    if update_examples and generated_config != expected_config:
        write_flow_yaml(spec, example_path)
    else:
        if generated_config != expected_config:
            diff = DeepDiff(expected_config, generated_config, verbose_level=2)
            error_msg = (
                f"\nConfig mismatch for: {file_name}\n"
                f"Expected file: {example_path}\n\n"
                f"Differences:\n{diff.pretty()}"
            )
            raise AssertionError(error_msg)
