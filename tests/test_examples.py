"""Test that Python code blocks in README.md and examples are valid and executable."""

from pathlib import Path

from inspect_flow import FlowJob
from inspect_flow._util.module_util import execute_src_and_get_last_result
from inspect_flow.api import load_job

from tests.test_helpers.config_helpers import validate_config


def extract_python_blocks(markdown_content: str) -> list[tuple[int, str]]:
    """Extract Python code blocks from markdown content.

    Returns list of (line_number, code) tuples.
    """
    blocks = []
    in_python_block = False
    current_block = []
    block_start_line = 0

    for line_num, line in enumerate(markdown_content.split("\n"), 1):
        if line.strip().startswith("```python"):
            in_python_block = True
            block_start_line = line_num + 1
            current_block = []
        elif line.strip().startswith("```") and in_python_block:
            in_python_block = False
            if current_block:
                blocks.append((block_start_line, "\n".join(current_block)))
        elif in_python_block:
            current_block.append(line)

    return blocks


def test_readme_python_blocks() -> None:
    """Test that all Python code blocks in README.md are valid and produce expected results."""
    readme_path = Path(__file__).parent.parent / "README.md"
    content = readme_path.read_text()

    blocks = extract_python_blocks(content)
    assert len(blocks) == 2, (
        "Unexpected number of Python code blocks found in README.md"
    )

    for i, (line_num, code) in enumerate(blocks):
        job = execute_src_and_get_last_result(
            code, f"README.md:line {line_num}", {}, None
        )
        assert isinstance(job, FlowJob), (
            f"Code block at README.md:line {line_num} did not return an object"
        )
        validate_config(job, f"readme_example_{i + 1}.yaml")


def test_examples() -> None:
    """Test that all example Python config files are valid and produce expected results."""
    examples_dir = Path(__file__).parent.parent / "examples"
    example_files = [f for f in examples_dir.glob("*.py")]

    for file in example_files:
        job = load_job(str(file))
        validate_config(job, f"{file.stem}.yaml")
