"""Test that Python code blocks in docs, README.md and examples are valid and executable."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
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
    current_block: list[str] = []
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
        try:
            job = load_job(str(file))
            validate_config(job, f"{file.stem}.yaml")
        except Exception as e:
            raise AssertionError(
                f"Failed testing config: {file.name}\nSource file: {file}"
            ) from e


def test_dirty_git_check() -> None:
    """Test that dirty_git_check/including/config.py raises error due to uncommitted changes."""
    examples_dir = Path(__file__).parent.parent / "examples"
    dirty_git_check_dir = examples_dir / "dirty_git_check"
    config_path = dirty_git_check_dir / "including" / "config.py"

    if config_path.exists():
        # Mock subprocess.run to return empty output (clean repo)
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            job = load_job(str(dirty_git_check_dir / "_flow.py"))
            validate_config(job, "dirty_git_check_flow.yaml")

        # Mock subprocess.run to return output indicating uncommitted changes
        mock_result = MagicMock()
        mock_result.stdout = "M  some_file.py\n"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="has uncommitted changes"):
                load_job(str(config_path))


def test_lock() -> None:
    """Test that lock/including/config.py raises error due to max_samples override."""
    examples_dir = Path(__file__).parent.parent / "examples"
    lock_dir = examples_dir / "lock"
    config_path = lock_dir / "including" / "config.py"

    if lock_dir.exists():
        job = load_job(str(lock_dir / "_flow.py"))
        validate_config(job, "lock_flow.yaml")

    if config_path.exists():
        with pytest.raises(ValueError, match="Do not override max_samples"):
            load_job(str(config_path))
