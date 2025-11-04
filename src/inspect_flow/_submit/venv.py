import json
import os
import subprocess
from importlib.metadata import Distribution, PackageNotFoundError
from pathlib import Path
from typing import List, Literal

import yaml
from pydantic import BaseModel, Field

from inspect_flow._types.flow_types import FConfig, FModel, FTask


class VcsInfo(BaseModel):
    vcs: Literal["git", "hg", "bzr", "svn"]
    commit_id: str
    requested_revision: str | None = None
    resolved_revision: str | None = None


class ArchiveInfo(BaseModel):
    hash: str | None = None  # Deprecated format: "<algorithm>=<hash>"
    hashes: dict[str, str] | None = None  # New format: {"sha256": "<hex>"}


class DirInfo(BaseModel):
    editable: bool = Field(default=False)  # Default: False


class DirectUrl(BaseModel):
    url: str
    vcs_info: VcsInfo | None = None
    archive_info: ArchiveInfo | None = None
    dir_info: DirInfo | None = None
    subdirectory: str | None = None


def get_package_direct_url(package: str) -> DirectUrl | None:
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
        return DirectUrl.model_validate_json(json_text)
    except (json.JSONDecodeError, ValueError):
        return None


def package_is_installed_editable(package: str) -> bool:
    return (
        (direct_url := get_package_direct_url(package)) is not None
        and direct_url.dir_info is not None
        and direct_url.dir_info.editable
    )


def direct_url_to_pip_string(direct_url: DirectUrl) -> str:
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


def get_pip_string(package: str) -> str:
    direct_url = get_package_direct_url(package)
    # If DirectURL is None, could be running in dev mode or installed from PyPI.
    if direct_url is None:
        package_path = Path(__file__).parents[3]
        if not (package_path / "pyproject.toml").exists():
            # Assume installed from PyPI
            return package
        return str(package_path)
    # package is installed - copy the installed package to the new venv
    return direct_url_to_pip_string(direct_url)


# TODO:ransom how do we keep in sync with inspect_ai - should probably export from there
providers = {
    "groq": "groq",
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google-genai",
    "hf": None,
    "vllm": "vllm",
    "cf": None,
    "mistral": "mistralai",
    "grok": "openai",
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
    "goodfire": "goodfire",
    "hf-inference-providers": "openai",
}


def get_model_dependencies(config: FConfig) -> List[str]:
    model_dependencies: set[str] = set()

    def collect_dependency(model_name: str) -> None:
        """Extract provider from model name like 'openai/gpt-4o-mini' -> 'openai'"""
        if "/" in model_name:
            dependency = providers.get(model_name.split("/")[0])
            if dependency:
                model_dependencies.add(dependency)

    def collect_model_dependencies(config: FTask) -> None:
        if config.model:
            collect_dependency(config.model.name)
        if config.model_roles:
            for model_role in config.model_roles.values():
                if isinstance(model_role, FModel):
                    collect_dependency(model_role.name)
                else:
                    collect_dependency(model_role)

    for task in config.tasks:
        collect_model_dependencies(task)

    return sorted(model_dependencies)


def create_venv(config: FConfig, temp_dir: str) -> dict[str, str]:
    flow_yaml_path = Path(temp_dir) / "flow.yaml"
    with open(flow_yaml_path, "w") as f:
        yaml.dump(
            config.model_dump(mode="json", exclude_unset=True),
            f,
            default_flow_style=False,
            sort_keys=False,
        )

    # Remove VIRTUAL_ENV from environment to avoid virtual environment confusion
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)

    command = ["uv", "venv"]
    if config.python_version:
        command.extend(["--python", config.python_version])
    subprocess.run(
        command,
        cwd=temp_dir,
        check=True,
        env=env,
    )

    dependencies: List[str] = config.dependencies or []
    dependencies = [
        dep if not dep.startswith(".") else str(Path(dep).resolve())
        for dep in dependencies
    ]
    dependencies.extend(get_model_dependencies(config))
    dependencies.append(get_pip_string("inspect-flow"))

    subprocess.run(
        ["uv", "pip", "install", *sorted(dependencies)],
        cwd=temp_dir,
        check=True,
        env=env,
    )

    return env
