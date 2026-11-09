import json
import os
import tomllib
from collections.abc import Collection, Mapping
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

# Flow's default dependency cooldown. tests/test_dependency_cooldown.py keeps it
# in step with [tool.uv] in flow's own pyproject.toml.
DEFAULT_COOLDOWN = timedelta(days=7)
SHORT_COOLDOWN = timedelta(hours=6)
SHORT_COOLDOWN_PACKAGES = ("anthropic", "inspect-ai", "inspect-scout", "openai")


def uv_settings_env(
    env: Mapping[str, str],
    config_dir: str,
    default: bool = True,
    host_pins: Collection[str] = (),
) -> dict[str, str]:
    # uv reads its system config from the first XDG_CONFIG_DIRS entry with a
    # uv/uv.toml. Flow's settings go there, so the user's project, user, env and
    # command-line settings override them one setting at a time, by uv's rules.
    # That file replaces the real system config, so its settings are copied in.
    settings = _system_settings(env)
    now = datetime.now(UTC)
    packages: dict[str, str] = {}
    if default:
        settings.setdefault("exclude-newer", _timestamp(now - DEFAULT_COOLDOWN))
        packages.update(
            {p: _timestamp(now - SHORT_COOLDOWN) for p in SHORT_COOLDOWN_PACKAGES}
        )
    # A version copied from the host is already running there, so the cooldown
    # must not reject it.
    packages.update({p: _timestamp(now) for p in _pinned_names(host_pins)})
    packages.update(
        {
            canonicalize_name(p): cutoff
            for p, cutoff in settings.get("exclude-newer-package", {}).items()
        }
    )
    if packages:
        settings["exclude-newer-package"] = packages

    config_file = Path(config_dir) / "uv" / "uv.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        "".join(f"{_toml(k)} = {_toml(v)}\n" for k, v in settings.items())
    )
    config_dirs = env.get("XDG_CONFIG_DIRS") or "/etc/xdg"
    return {**env, "XDG_CONFIG_DIRS": os.pathsep.join([config_dir, config_dirs])}


def _system_settings(env: Mapping[str, str]) -> dict[str, Any]:
    # Where uv looks, per https://docs.astral.sh/uv/concepts/configuration-files/
    for directory in (env.get("XDG_CONFIG_DIRS") or "/etc/xdg").split(os.pathsep):
        if directory and (Path(directory) / "uv" / "uv.toml").is_file():
            return _read_toml(Path(directory) / "uv" / "uv.toml")
    if Path("/etc/uv/uv.toml").is_file():
        return _read_toml(Path("/etc/uv/uv.toml"))
    return {}


def _read_toml(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _toml(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(_toml(v) for v in value) + "]"
    if isinstance(value, dict):
        items = (f"{_toml(k)} = {_toml(v)}" for k, v in value.items())
        return "{" + ", ".join(items) + "}"
    raise TypeError(f"Cannot write {type(value).__name__} to uv.toml")


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
