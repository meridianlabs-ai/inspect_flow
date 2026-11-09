import os
from collections.abc import Collection, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from logging import getLogger
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

logger = getLogger(__name__)

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
    # A real system config or an explicit config file is left to work alone.
    if user_config_file(env):
        return dict(env)
    now = datetime.now(UTC)
    packages: dict[str, str] = {}
    lines: list[str] = []
    if default:
        lines.append(f'exclude-newer = "{_timestamp(now - DEFAULT_COOLDOWN)}"')
        packages.update(
            {p: _timestamp(now - SHORT_COOLDOWN) for p in SHORT_COOLDOWN_PACKAGES}
        )
    # A version copied from the host is already running there, so the cooldown
    # must not reject it.
    packages.update({p: _timestamp(now) for p in _pinned_names(host_pins)})
    if packages:
        lines.append("[exclude-newer-package]")
        lines.extend(f'"{p}" = "{cutoff}"' for p, cutoff in packages.items())

    config_file = Path(config_dir) / "uv" / "uv.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("".join(f"{line}\n" for line in lines))
    config_dirs = env.get("XDG_CONFIG_DIRS") or "/etc/xdg"
    return {**env, "XDG_CONFIG_DIRS": os.pathsep.join([config_dir, config_dirs])}


def user_config_file(env: Mapping[str, str]) -> str | None:
    # The explicit or system config file uv reads, which Flow's settings would
    # replace. Only its existence is checked: uv reads it, Flow does not.
    if env.get("UV_CONFIG_FILE"):
        return env["UV_CONFIG_FILE"]
    if _flag(env, "UV_NO_CONFIG") or _flag(env, "UV_NO_SYSTEM_CONFIG"):
        return None
    # Where uv looks, per https://docs.astral.sh/uv/concepts/configuration-files/
    for directory in (env.get("XDG_CONFIG_DIRS") or "/etc/xdg").split(os.pathsep):
        if directory and (Path(directory) / "uv" / "uv.toml").is_file():
            return str(Path(directory) / "uv" / "uv.toml")
    return "/etc/uv/uv.toml" if Path("/etc/uv/uv.toml").is_file() else None


def config_file_arg(args: Sequence[str]) -> str | None:
    for i, arg in enumerate(args):
        if arg == "--config-file" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--config-file="):
            return arg.removeprefix("--config-file=")
    return None


def warn_no_default_cooldown(config_file: str, scope: str = "this run") -> None:
    logger.warning(
        f"uv reads {config_file}, so Flow's default release cooldown is off for "
        f"{scope}. Set exclude-newer in that file to add one."
    )


def _flag(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").lower() in ("1", "true", "yes", "on")


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
