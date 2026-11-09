import tomllib
from collections.abc import Collection, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

# Flow's default dependency cooldown, used for whatever the user's uv settings
# leave unset. tests/test_dependency_cooldown.py keeps it in step with
# [tool.uv] in flow's own pyproject.toml.
DEFAULT_COOLDOWN = timedelta(days=7)
SHORT_COOLDOWN = timedelta(hours=6)
SHORT_COOLDOWN_PACKAGES = ("anthropic", "inspect-ai", "inspect-scout", "openai")

_TRUE = ("1", "true", "t", "yes", "y", "on")


def uv_cooldown_args(
    project_dir: str | None,
    env: Mapping[str, str],
    pip: bool,
    host_pins: Collection[str] = (),
    default: bool = True,
) -> list[str]:
    configured, configured_packages = _configured_exclude_newer(project_dir, env, pip)
    now = datetime.now(UTC)
    args: list[str] = []
    cutoffs: dict[str, datetime] = {}
    if default:
        if not configured:
            args += ["--exclude-newer", _timestamp(now - DEFAULT_COOLDOWN)]
        cutoffs.update({p: now - SHORT_COOLDOWN for p in SHORT_COOLDOWN_PACKAGES})
    # A version copied from the host is already running there, so the cooldown
    # must not reject it.
    cutoffs.update({p: now for p in _pinned_names(host_pins)})
    for package, cutoff in sorted(cutoffs.items()):
        if package not in configured_packages:
            args += ["--exclude-newer-package", f"{package}={_timestamp(cutoff)}"]
    return args


def _pinned_names(requirements: Collection[str]) -> set[str]:
    names: set[str] = set()
    for requirement in requirements:
        try:
            parsed = Requirement(requirement)
        except InvalidRequirement:
            continue
        if any(
            s.operator in ("==", "===") and not s.version.endswith(".*")
            for s in parsed.specifier
        ):
            names.add(canonicalize_name(parsed.name))
    return names


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _configured_exclude_newer(
    project_dir: str | None, env: Mapping[str, str], pip: bool
) -> tuple[bool, set[str]]:
    configured = bool(env.get("UV_EXCLUDE_NEWER"))
    packages: set[str] = set()
    for options in _uv_config_options(project_dir, env):
        # `uv pip` commands also read the `pip` section.
        sections = [options, options.get("pip", {})] if pip else [options]
        for section in sections:
            configured = configured or "exclude-newer" in section
            packages.update(
                canonicalize_name(p) for p in section.get("exclude-newer-package", {})
            )
    return configured, packages


def _uv_config_options(
    project_dir: str | None, env: Mapping[str, str]
) -> list[dict[str, Any]]:
    # The configuration files uv reads, per
    # https://docs.astral.sh/uv/concepts/configuration-files/
    if env.get("UV_NO_CONFIG", "").lower() in _TRUE:
        return []
    if config_file := env.get("UV_CONFIG_FILE"):
        return [_read_toml(Path(config_file))]
    options = [
        _project_options(Path(project_dir)) if project_dir else None,
        _file_options(_user_config_file(env)),
        _file_options(_system_config_file(env)),
    ]
    return [o for o in options if o is not None]


def _project_options(directory: Path) -> dict[str, Any] | None:
    for current in [directory, *directory.parents]:
        if (current / "uv.toml").is_file():
            return _read_toml(current / "uv.toml")
        pyproject = current / "pyproject.toml"
        if pyproject.is_file():
            uv = _read_toml(pyproject).get("tool", {}).get("uv")
            if uv is not None:
                return uv
    return None


def _user_config_file(env: Mapping[str, str]) -> Path:
    config_home = env.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config_home) / "uv" / "uv.toml"


def _system_config_file(env: Mapping[str, str]) -> Path:
    for directory in (env.get("XDG_CONFIG_DIRS") or "/etc/xdg").split(":"):
        if directory and (Path(directory) / "uv" / "uv.toml").is_file():
            return Path(directory) / "uv" / "uv.toml"
    return Path("/etc/uv/uv.toml")


def _file_options(path: Path) -> dict[str, Any] | None:
    return _read_toml(path) if path.is_file() else None


def _read_toml(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)
