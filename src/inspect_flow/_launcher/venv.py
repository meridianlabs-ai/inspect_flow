import os
import shlex
import subprocess
import sys
import tempfile
from logging import getLogger
from pathlib import Path
from typing import List, Literal, Sequence

import yaml
from dotenv import dotenv_values, find_dotenv
from inspect_ai._util.file import absolute_file_path

from inspect_flow._launcher.auto_dependencies import collect_auto_dependencies
from inspect_flow._launcher.freeze import write_flow_requirements
from inspect_flow._launcher.pip_string import get_pip_string
from inspect_flow._launcher.python_version import resolve_python_version
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.args import MODEL_DUMP_ARGS
from inspect_flow._util.logging import get_last_log_level
from inspect_flow._util.path_util import absolute_path_relative_to
from inspect_flow._util.subprocess_util import run_with_logging

logger = getLogger(__name__)


def venv_launch(spec: FlowSpec, base_dir: str, dry_run: bool, no_dotenv: bool) -> None:
    run_path = (Path(__file__).parents[1] / "_runner" / "run.py").absolute()
    base_dir = absolute_file_path(base_dir)
    run_args = ["--dry-run"] if dry_run else []
    args = ["--base-dir", base_dir, "--log-level", get_last_log_level()] + run_args

    with tempfile.TemporaryDirectory() as temp_dir:
        env = _get_env(base_dir, no_dotenv=no_dotenv)
        if spec.env:
            env.update(**spec.env)

        # Set the virtual environment so that it will be created in the temp directory
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")

        _create_venv(
            spec, base_dir=base_dir, temp_dir=temp_dir, env=env, dry_run=dry_run
        )

        python_path = Path(temp_dir) / ".venv" / "bin" / "python"
        file = _write_flow_yaml(spec, temp_dir)
        subprocess.run(
            [str(python_path), str(run_path), "--file", file.as_posix(), *args],
            check=True,
            env=env,
        )


def _create_venv(
    spec: FlowSpec,
    base_dir: str,
    temp_dir: str,
    env: dict[str, str],
    dry_run: bool = False,
) -> None:
    _create_venv_with_base_dependencies(
        spec, base_dir=base_dir, temp_dir=temp_dir, env=env
    )

    dependencies: List[str] = []
    if spec.dependencies and spec.dependencies.additional_dependencies:
        if isinstance(spec.dependencies.additional_dependencies, str):
            dependencies.append(spec.dependencies.additional_dependencies)
        else:
            dependencies.extend(spec.dependencies.additional_dependencies)
        dependencies = [
            _resolve_dependency(dep, base_dir=base_dir) for dep in dependencies
        ]

    auto_detect_dependencies = True
    if spec.dependencies and spec.dependencies.auto_detect_dependencies is False:
        auto_detect_dependencies = False

    if auto_detect_dependencies:
        dependencies.extend(collect_auto_dependencies(spec))
    dependencies.append(get_pip_string("inspect-flow"))

    _uv_pip_install(dependencies, temp_dir, env)

    write_flow_requirements(spec, temp_dir, env, dry_run)


def _resolve_dependency(dependency: str, base_dir: str) -> str:
    if "/" in dependency:
        return absolute_path_relative_to(dependency, base_dir=base_dir)
    return dependency


def _create_venv_with_base_dependencies(
    spec: FlowSpec, base_dir: str, temp_dir: str, env: dict[str, str]
) -> None:
    file_type: Literal["requirements.txt", "pyproject.toml"] | None = None
    file_path: str | None = None
    dependency_file_info = _get_dependency_file(spec, base_dir=base_dir)
    if not dependency_file_info:
        logger.info("No dependency file found, creating bare venv")
        _uv_venv(spec, temp_dir, env)
        return

    file_type, file_path = dependency_file_info
    if file_type == "requirements.txt":
        logger.info(f"Using requirements.txt to create venv. File: {file_path}")
        _uv_venv(spec, temp_dir, env)
        # Need to run in the directory containing the requirements.txt to handle relative paths
        _uv_pip_install(["-r", file_path], Path(file_path).parent.as_posix(), env)
        return

    logger.info(f"Using pyproject.toml to create venv. File: {file_path}")
    project_dir = Path(file_path).parent
    if not spec.python_version:
        spec.python_version = resolve_python_version(file_path)

    uv_args = [
        "--no-dev",
        "--python",
        spec.python_version,
        "--project",
        str(project_dir),
        "--active",
    ]
    if (project_dir / "uv.lock").exists():
        uv_args.append("--frozen")

    uv_args.extend(_uv_sync_args(spec))

    logger.info(f"Creating venv with uv args: {uv_args}")
    run_with_logging(
        ["uv", "sync"] + uv_args,
        cwd=temp_dir,
        env=env,
    )


def _uv_sync_args(spec: FlowSpec) -> Sequence[str]:
    if spec.dependencies and spec.dependencies.uv_sync_args:
        if isinstance(spec.dependencies.uv_sync_args, str):
            return shlex.split(spec.dependencies.uv_sync_args)
        else:
            return spec.dependencies.uv_sync_args
    return []


def _uv_venv(spec: FlowSpec, temp_dir: str, env: dict[str, str]) -> None:
    spec.python_version = (
        spec.python_version
        or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    run_with_logging(
        ["uv", "venv", "--python", spec.python_version],
        cwd=temp_dir,
        env=env,
    )


def _uv_pip_install(args: List[str], temp_dir: str, env: dict[str, str]) -> None:
    """Install packages using 'uv pip install'."""
    run_with_logging(
        ["uv", "pip", "install"] + args,
        cwd=temp_dir,
        env=env,
    )


def _get_dependency_file(
    spec: FlowSpec, base_dir: str
) -> tuple[Literal["requirements.txt", "pyproject.toml"], str] | None:
    if spec.dependencies and spec.dependencies.dependency_file == "no_file":
        return None

    if (
        not spec.dependencies
        or not spec.dependencies.dependency_file
        or spec.dependencies.dependency_file == "auto"
    ):
        return _search_dependency_file(base_dir=base_dir)

    file = absolute_path_relative_to(
        spec.dependencies.dependency_file, base_dir=base_dir
    )
    if not Path(file).exists():
        raise FileNotFoundError(f"Dependency file '{file}' does not exist.")
    if file.endswith("pyproject.toml"):
        return "pyproject.toml", file
    return "requirements.txt", file


def _search_dependency_file(
    base_dir: str,
) -> tuple[Literal["requirements.txt", "pyproject.toml"], str] | None:
    files: list[Literal["pyproject.toml", "requirements.txt"]] = [
        "pyproject.toml",
        "requirements.txt",
    ]

    # Walk up the directory tree starting from base_dir
    current_dir = Path(base_dir).resolve()
    found_file = None
    found_path = None
    while True:
        for file_name in files:
            file_path = current_dir / file_name
            if file_path.exists():
                if not found_file:
                    found_file = file_name
                    found_path = str(file_path)
                else:
                    logger.warning(
                        f"Multiple dependency files found when auto-detecting dependencies. "
                        f"Using '{found_file}' at '{found_path}' and ignoring "
                        f"'{file_name}' at '{file_path}'."
                    )

        # Move to parent directory
        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent
    return (found_file, found_path) if found_file and found_path else None


def _write_flow_yaml(spec: FlowSpec, dir: str) -> Path:
    flow_yaml_path = Path(dir) / "flow.yaml"
    with open(flow_yaml_path, "w") as f:
        yaml.dump(
            spec.model_dump(**MODEL_DUMP_ARGS),
            f,
            default_flow_style=False,
            sort_keys=False,
        )
    return flow_yaml_path


def _get_env(base_dir: str, no_dotenv: bool) -> dict[str, str]:
    env = os.environ.copy()
    if no_dotenv:
        return env
    # Temporarily change to base_dir to find .env file
    original_cwd = os.getcwd()
    try:
        os.chdir(base_dir)
        # Already loaded environment variables should take precedence
        dotenv = dotenv_values(find_dotenv(usecwd=True))
        env = {k: v for k, v in dotenv.items() if v is not None} | env
    finally:
        os.chdir(original_cwd)
    return env
