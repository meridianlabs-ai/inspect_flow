import subprocess
import sys
from pathlib import Path
from typing import List, Literal

import click
import yaml

from inspect_flow._launcher.auto_dependencies import collect_auto_dependencies
from inspect_flow._launcher.pip_string import get_pip_string
from inspect_flow._types.flow_types import (
    FlowJob,
)
from inspect_flow._util.path_util import absolute_path_relative_to


def create_venv(
    job: FlowJob, base_dir: str, temp_dir: str, env: dict[str, str]
) -> None:
    flow_yaml_path = Path(temp_dir) / "flow.yaml"
    job.python_version = (
        job.python_version
        or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    with open(flow_yaml_path, "w") as f:
        yaml.dump(
            job.model_dump(mode="json", exclude_unset=True),
            f,
            default_flow_style=False,
            sort_keys=False,
        )

    _create_venv_with_base_dependencies(
        job, base_dir=base_dir, temp_dir=temp_dir, env=env
    )

    dependencies: List[str] = []
    if job.dependencies and job.dependencies.additional_dependencies:
        dependencies.extend(job.dependencies.additional_dependencies)
        dependencies = [
            dep if not dep.startswith(".") else str(Path(dep).resolve())
            for dep in dependencies
        ]

    auto_detect_dependencies = True
    if job.dependencies and job.dependencies.auto_detect_dependencies is not None:
        auto_detect_dependencies = job.dependencies.auto_detect_dependencies

    if auto_detect_dependencies:
        dependencies.extend(collect_auto_dependencies(job))
    dependencies.append(get_pip_string("inspect-flow"))

    _uv_pip_install(sorted(dependencies), temp_dir, env)

    # Freeze installed packages to flow_requirements.txt in log_dir
    if job.log_dir:
        freeze_result = subprocess.run(
            ["uv", "pip", "freeze"],
            cwd=temp_dir,
            check=True,
            env=env,
            capture_output=True,
            text=True,
        )
        log_dir_path = Path(job.log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        requirements_path = log_dir_path / "flow_requirements.txt"
        requirements_path.write_text(freeze_result.stdout)


def _create_venv_with_base_dependencies(
    job: FlowJob, base_dir: str, temp_dir: str, env: dict[str, str]
) -> None:
    file_type: Literal["requirements.txt", "pyproject.toml"] | None = None
    file_path: str | None = None
    dependency_file_info = _get_dependency_file(job, base_dir=base_dir)
    if not dependency_file_info:
        click.echo("No dependency file found, creating bare venv")
        _uv_venv(job, temp_dir, env)
        return

    file_type, file_path = dependency_file_info
    if file_type == "requirements.txt":
        click.echo(f"Using requirements.txt to create venv. File: {file_path}")
        _uv_venv(job, temp_dir, env)
        _uv_pip_install(["-r", file_path], temp_dir, env)
        return

    click.echo(f"Using pyproject.toml to create venv. File: {file_path}")
    assert job.python_version
    project_dir = Path(file_path).parent
    uv_args = [
        "--python",
        job.python_version,
        "--project",
        str(project_dir),
        "--active",
    ]
    if (project_dir / "uv.lock").exists():
        uv_args.append("--frozen")
    click.echo(f"Creating venv with uv args: {uv_args}")
    subprocess.run(
        ["uv", "sync", "--no-dev"] + uv_args,
        cwd=temp_dir,
        check=True,
        env=env,
    )


def _uv_venv(job: FlowJob, temp_dir: str, env: dict[str, str]) -> None:
    """Create a virtual environment using 'uv venv'."""
    assert job.python_version
    subprocess.run(
        ["uv", "venv", "--python", job.python_version],
        cwd=temp_dir,
        check=True,
        env=env,
    )


def _uv_pip_install(args: List[str], temp_dir: str, env: dict[str, str]) -> None:
    """Install packages using 'uv pip install'."""
    subprocess.run(
        ["uv", "pip", "install"] + args,
        cwd=temp_dir,
        check=True,
        env=env,
    )


def _get_dependency_file(
    job: FlowJob, base_dir: str
) -> tuple[Literal["requirements.txt", "pyproject.toml"], str] | None:
    mode = job.dependencies and job.dependencies.dependency_file_mode or "auto"
    if mode == "no_file":
        return None

    file = job.dependencies and job.dependencies.dependency_file or None
    if file:
        file = absolute_path_relative_to(file, base_dir=base_dir)
        if not Path(file).exists():
            raise FileNotFoundError(f"Dependency file '{file}' does not exist.")
        if mode != "auto":
            return mode, file
        if file.endswith("requirements.txt"):
            return "requirements.txt", file
        if file.endswith("pyproject.toml"):
            return "pyproject.toml", file
        raise ValueError(
            f"Cannot determine dependency file type from '{file}'. "
            "Please set dependency_file_mode to 'requirements.txt' or 'pyproject.toml'."
        )
    files: list[Literal["pyproject.toml", "requirements.txt"]] = (
        ["pyproject.toml", "requirements.txt"] if mode == "auto" else [mode]
    )

    # Walk up the directory tree starting from base_dir
    current_dir = Path(base_dir).resolve()
    while True:
        for file_name in files:
            file_path = current_dir / file_name
            if file_path.exists():
                return file_name, str(file_path)

        # Move to parent directory
        parent = current_dir.parent
        if parent == current_dir:  # Reached root directory
            break
        current_dir = parent

    return None
