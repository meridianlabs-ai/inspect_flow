import json
from importlib.metadata import Distribution, PackageNotFoundError
from logging import getLogger
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

logger = getLogger(__name__)


def get_pip_string(package: str) -> str:
    direct_url = _get_package_direct_url(package)
    if direct_url:
        # package is installed - copy the installed package to the new venv
        return _direct_url_to_pip_string(direct_url)
    if package != "inspect-flow":
        return _get_pip_string_with_version(package)
    # If DirectURL is None, inspect-flow could be running in dev mode or installed from PyPI.
    package_path = Path(__file__).parents[3]
    if not (package_path / "pyproject.toml").exists():
        # Assume installed from PyPI
        return _get_pip_string_with_version(package)
    return str(package_path)


def _get_pip_string_with_version(package: str) -> str:
    """Return package name with exact version specifier if version can be determined."""
    try:
        version = Distribution.from_name(package).version
        return f"{package}=={version}"
    except (ValueError, PackageNotFoundError) as e:
        logger.info(f"Could not determine version for package '{package}': {e}.")
        return package


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
