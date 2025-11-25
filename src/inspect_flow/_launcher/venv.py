import json
import subprocess
import sys
from importlib.metadata import Distribution, PackageNotFoundError
from pathlib import Path
from typing import List, Literal

import click
import yaml
from inspect_ai._util.registry import (
    registry_find,
    registry_info,
    registry_package_name,
)
from inspect_ai.util import SandboxEnvironmentType
from inspect_ai.util._sandbox.registry import registry_match_sandboxenv
from pydantic import BaseModel, Field

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowJob,
    FlowModel,
    FlowSolver,
    FlowTask,
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
        dependencies.extend(_collect_auto_dependencies(job))
    dependencies.append(_get_pip_string("inspect-flow"))

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


class _VcsInfo(BaseModel):
    vcs: Literal["git", "hg", "bzr", "svn"]
    commit_id: str
    requested_revision: str | None = None
    resolved_revision: str | None = None


class _ArchiveInfo(BaseModel):
    hash: str | None = None  # Deprecated format: "<algorithm>=<hash>"
    hashes: dict[str, str] | None = None  # New format: {"sha256": "<hex>"}


class _DirInfo(BaseModel):
    editable: bool = Field(default=False)  # Default: False


class _DirectUrl(BaseModel):
    url: str
    vcs_info: _VcsInfo | None = None
    archive_info: _ArchiveInfo | None = None
    dir_info: _DirInfo | None = None
    subdirectory: str | None = None


def _get_package_direct_url(package: str) -> _DirectUrl | None:
    """Retrieve the PEP 610 direct_url.json

    `direct_url.json` is a metadata file created by pip (and other Python package
    installers) in the .dist-info directory of installed packages. It's defined by
    PEP 610 and records how a package was installed when it came from a direct URL
    source rather than PyPI.

    When is it created?

    This file is created when installing packages via:
    - Git URLs: pip install git+https://github.com/user/repo.git
    - Local directories: pip install /path/to/package
    - Editable installs: pip install -e /path/to/package or pip install -e git+...
    - Direct archive URLs: pip install https://example.com/package.tar.gz
    """
    try:
        distribution = Distribution.from_name(package)
    except (ValueError, PackageNotFoundError):
        return None

    if (json_text := distribution.read_text("direct_url.json")) is None:
        return None

    try:
        return _DirectUrl.model_validate_json(json_text)
    except (json.JSONDecodeError, ValueError):
        return None


def _direct_url_to_pip_string(direct_url: _DirectUrl) -> str:
    """Convert a DirectUrl object to a pip install argument string."""
    # VCS install (git, hg, bzr, svn)
    if direct_url.vcs_info:
        vcs = direct_url.vcs_info.vcs
        url = direct_url.url
        pip_string = f"{vcs}+{url}"

        if direct_url.vcs_info.commit_id:
            pip_string += f"@{direct_url.vcs_info.commit_id}"

        if direct_url.subdirectory:
            pip_string += f"#subdirectory={direct_url.subdirectory}"

        return pip_string

    # Editable install
    if direct_url.dir_info and direct_url.dir_info.editable:
        url = direct_url.url
        if url.startswith("file://"):
            url = url[7:]  # Strip file:// prefix
        return f"-e {url}"

    # Local directory (non-editable)
    if direct_url.dir_info:
        return direct_url.url

    # Archive/wheel with optional hash
    if direct_url.archive_info:
        url = direct_url.url

        if direct_url.archive_info.hashes:
            for algo, hash_val in direct_url.archive_info.hashes.items():
                url += f"#{algo}={hash_val}"
                break
        elif direct_url.archive_info.hash:
            url += f"#{direct_url.archive_info.hash}"

        return url

    # Fallback: just the URL
    return direct_url.url


def _get_pip_string(package: str) -> str:
    direct_url = _get_package_direct_url(package)
    if direct_url:
        # package is installed - copy the installed package to the new venv
        return _direct_url_to_pip_string(direct_url)
    if package != "inspect-flow":
        return package
    # If DirectURL is None, inspect-flow could be running in dev mode or installed from PyPI.
    package_path = Path(__file__).parents[3]
    if not (package_path / "pyproject.toml").exists():
        # Assume installed from PyPI
        return package
    return str(package_path)


# TODO:ransom how do we keep in sync with inspect_ai - should probably export from there
_MODEL_PROVIDERS: dict[str, list[str]] = {
    "groq": ["groq"],
    "openai": ["openai"],
    "anthropic": ["anthropic"],
    "google": ["google-genai"],
    "hf": ["torch", "transformers", "accelerate"],
    "vllm": ["vllm"],
    "cf": [],
    "mistral": ["mistralai"],
    "grok": ["xai_sdk"],
    "together": ["openai"],
    "fireworks": ["openai"],
    "sambanova": ["openai"],
    "ollama": ["openai"],
    "openrouter": ["openai"],
    "perplexity": ["openai"],
    "llama-cpp-python": ["openai"],
    "azureai": ["azure-ai-inference"],
    "bedrock": [],
    "sglang": ["openai"],
    "transformer_lens": ["transformer_lens"],
    "hf-inference-providers": ["openai"],
}


def _collect_auto_dependencies(job: FlowJob) -> set[str]:
    result = set()

    for task in job.tasks or []:
        _collect_task_dependencies(task, result)

    return {_get_pip_string(dep) for dep in result}


def _collect_task_dependencies(task: FlowTask | str, dependencies: set[str]) -> None:
    if isinstance(task, str):
        return _collect_name_dependencies(task, dependencies)

    _collect_name_dependencies(task.name, dependencies)
    _collect_solver_dependencies(task.solver, dependencies)
    _collect_sandbox_dependencies(task.sandbox, dependencies)
    # TODO _collect_approver_dependencies(task.approver, dependencies)

    if task.model:
        _collect_model_dependencies(task.model, dependencies)
    if task.model_roles:
        for model_role in task.model_roles.values():
            _collect_model_dependencies(model_role, dependencies)


def _collect_name_dependencies(name: str | None, dependencies: set[str]) -> None:
    if name is None or name.find("@") != -1 or name.find(".py") != -1:
        # Looks like a file name, not a package name
        return
    split = name.split("/", maxsplit=1)
    if len(split) == 2:
        dependencies.add(split[0])


def _collect_model_dependencies(
    model: str | FlowModel | None, dependencies: set[str]
) -> None:
    name = model.name if isinstance(model, FlowModel) else model
    if name is None:
        return
    split = name.split("/", maxsplit=1)
    if len(split) == 2:
        dependencies.update(_MODEL_PROVIDERS.get(split[0], [split[0]]))


def _collect_solver_dependencies(
    solver: str | FlowSolver | list[str | FlowSolver] | FlowAgent | None,
    dependencies: set[str],
) -> None:
    if solver is None:
        return
    if isinstance(solver, str):
        return _collect_name_dependencies(solver, dependencies)
    if isinstance(solver, list):
        for s in solver:
            _collect_solver_dependencies(s, dependencies)
        return
    _collect_name_dependencies(solver.name, dependencies)


def _collect_sandbox_dependencies(
    sandbox: SandboxEnvironmentType | None,
    dependencies: set[str],
) -> None:
    if sandbox is None:
        return
    if isinstance(sandbox, str):
        return _collect_sandbox_type_dependencies(sandbox, dependencies)
    if isinstance(sandbox, tuple):
        return _collect_sandbox_type_dependencies(sandbox[0], dependencies)
    return _collect_sandbox_type_dependencies(sandbox.type, dependencies)


def _collect_sandbox_type_dependencies(
    sandbox_type: str,
    dependencies: set[str],
) -> None:
    entries = registry_find(registry_match_sandboxenv(sandbox_type))
    if not entries:
        click.echo(
            f"No matching sandbox environment found in registry for {sandbox_type}"
        )
        return
    info = registry_info(entries[0])
    if name := registry_package_name(info.name):
        dependencies.add(name)
