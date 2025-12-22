"""Utilities for reading and resolving Python version requirements."""

import re
import subprocess
import sys
from logging import getLogger
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from packaging.specifiers import SpecifierSet
from packaging.version import Version

logger = getLogger(__name__)


def _read_requires_python(pyproject_path: str | Path) -> str | None:
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    return data.get("project", {}).get("requires-python")


def _get_available_python_versions() -> list[Version]:
    """Get list of Python versions available for installation via uv.

    Returns:
        List of available Python versions, sorted from newest to oldest.
    """
    result = subprocess.run(
        ["uv", "python", "list", "--all-versions"],
        capture_output=True,
        text=True,
        check=True,
    )

    versions: list[Version] = []
    # Parse output like: "cpython-3.12.0-macos-aarch64-none"
    version_pattern = re.compile(r"cpython-(\d+\.\d+\.\d+)")

    for line in result.stdout.strip().split("\n"):
        match = version_pattern.search(line)
        if match:
            try:
                versions.append(Version(match.group(1)))
            except Exception:
                continue

    # Remove duplicates and sort descending
    unique_versions = sorted(set(versions), reverse=True)
    return unique_versions


def _find_best_python_version(
    specifier: str,
) -> Version | None:
    """Find the best Python version that satisfies a version specifier.

    Prefers the current version or newest version that satisfies the requirement.

    Args:
        specifier: PEP 440 version specifier (e.g., ">=3.10", ">=3.9,<3.12").

    Returns:
        The best matching Version, or None if no match found.
    """
    spec_set = SpecifierSet(specifier)

    current = Version(
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    if current in spec_set:
        return current

    available_versions = _get_available_python_versions()

    for version in available_versions:
        if version in spec_set:
            return version

    return None


def resolve_python_version(pyproject_path: str | Path) -> str:
    """Resolve the Python version to use based on pyproject.toml.

    Reads the requires-python field and finds the best available version.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        A version string like "3.12.0" that can be used with uv.

    Raises:
        FileNotFoundError: If pyproject.toml doesn't exist.
        ValueError: If no suitable Python version is found.
    """
    requires_python = _read_requires_python(pyproject_path)

    if not requires_python:
        # Fall back to current Python version
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        logger.info(f"No requires-python found, using current Python: {current}")
        return current

    logger.info(f"Found requires-python: {requires_python}")

    best_version = _find_best_python_version(requires_python)
    if best_version is None:
        raise ValueError(f"No available Python version satisfies: {requires_python}")

    logger.info(f"Selected Python version: {best_version}")
    return str(best_version)
