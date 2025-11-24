import json
import os
import shutil
import subprocess
import sys
from importlib.metadata import Distribution, PackageNotFoundError
from pathlib import Path
from typing import List, Literal

import yaml
from pydantic import BaseModel, Field

from inspect_flow._types.flow_types import FlowJob, FlowModel, FlowTask


def create_venv(job: FlowJob, base_dir: str, temp_dir: str) -> dict[str, str]:
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

    # Remove VIRTUAL_ENV from environment to avoid virtual environment confusion
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)

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
    dependencies.extend(_get_model_dependencies(job))
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

    return env


def _create_venv_with_base_dependencies(
    job: FlowJob, base_dir: str, temp_dir: str, env: dict[str, str]
) -> None:
    file_type: Literal["requirements.txt", "pyproject.toml"] | None = None
    file_path: str | None = None
    dependency_file_info = _get_dependency_file(job, base_dir=base_dir)
    if not dependency_file_info:
        _uv_venv(job, temp_dir, env)
        return

    file_type, file_path = dependency_file_info
    if file_type == "requirements.txt":
        _uv_venv(job, temp_dir, env)
        _uv_pip_install(["-r", file_path], temp_dir, env)
        return

    assert job.python_version
    shutil.copy(file_path, Path(temp_dir) / "pyproject.toml")
    use_uv_lock = (
        False if job.dependencies and job.dependencies.use_uv_lock is False else True
    )
    uv_lock_file = Path(file_path).parent / "uv.lock"
    if not uv_lock_file.exists():
        use_uv_lock = False
    if use_uv_lock:
        shutil.copy(uv_lock_file, Path(temp_dir) / "uv.lock")
    else:
        subprocess.run(
            ["uv", "lock", "--python", job.python_version],
            cwd=temp_dir,
            check=True,
            env=env,
        )
    subprocess.run(
        ["uv", "sync", "--no-dev", "--frozen", "--python", job.python_version],
        cwd=temp_dir,
        check=True,
        env=env,
    )


def _uv_venv(job: FlowJob, temp_dir: str, env: dict[str, str]) -> None:
    """Create a virtual environment using 'uv venv'."""
    assert job.python_version
    command = ["uv", "venv"]
    command.extend(["--python", job.python_version])
    subprocess.run(
        command,
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
    if mode == "none":
        return None

    file = job.dependencies and job.dependencies.dependency_file or None
    if file:
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
    # If DirectURL is None, could be running in dev mode or installed from PyPI.
    if direct_url is None:
        package_path = Path(__file__).parents[3]
        if not (package_path / "pyproject.toml").exists():
            # Assume installed from PyPI
            return package
        return str(package_path)
    # package is installed - copy the installed package to the new venv
    return _direct_url_to_pip_string(direct_url)


# TODO:ransom how do we keep in sync with inspect_ai - should probably export from there
_providers: dict[str, str | list[str] | None] = {
    "groq": "groq",
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google-genai",
    "hf": ["torch", "transformers", "accelerate"],
    "vllm": "vllm",
    "cf": None,
    "mistral": "mistralai",
    "grok": "xai_sdk",
    "together": "openai",
    "fireworks": "openai",
    "sambanova": "openai",
    "ollama": "openai",
    "openrouter": "openai",
    "perplexity": "openai",
    "llama-cpp-python": "openai",
    "azureai": "azure-ai-inference",
    "bedrock": None,
    "sglang": "openai",
    "transformer_lens": "transformer_lens",
    "hf-inference-providers": "openai",
}


def _get_model_dependencies(config: FlowJob) -> List[str]:
    model_dependencies: set[str] = set()

    def collect_dependency(model_name: str | None) -> None:
        """Extract provider from model name like 'openai/gpt-4o-mini' -> 'openai'"""
        if model_name and "/" in model_name:
            dependency = _providers.get(model_name.split("/")[0])
            if dependency:
                if isinstance(dependency, list):
                    model_dependencies.update(dependency)
                else:
                    model_dependencies.add(dependency)

    def collect_model_dependencies(config: FlowTask) -> None:
        if config.model:
            collect_dependency(config.model_name)
        if config.model_roles:
            for model_role in config.model_roles.values():
                if isinstance(model_role, FlowModel):
                    collect_dependency(model_role.name)
                else:
                    collect_dependency(model_role)

    for task in config.tasks or []:
        if isinstance(task, FlowTask):
            collect_model_dependencies(task)

    return sorted(model_dependencies)
