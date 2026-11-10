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
    pins: Collection[str] = (),
) -> dict[str, str]:
    # uv reads its system config from the first XDG_CONFIG_DIRS entry with a
    # uv/uv.toml. Flow's settings go there, so the user's project, user, env and
    # command-line settings override them one setting at a time, by uv's rules.
    # A real system config or an explicit config file is left to work alone.
    if user_config_file(env):
        return dict(env)
    now = datetime.now(UTC)
    packages = {p: _timestamp(now - SHORT_COOLDOWN) for p in SHORT_COOLDOWN_PACKAGES}
    # A version copied from the host must not be rejected by the cooldown.
    packages.update({p: _timestamp(now) for p in _exact_pins(pins)})
    lines = [
        f'exclude-newer = "{_timestamp(now - DEFAULT_COOLDOWN)}"',
        "[exclude-newer-package]",
        *(f'"{p}" = "{cutoff}"' for p, cutoff in packages.items()),
    ]

    config_file = Path(config_dir) / "uv" / "uv.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("".join(f"{line}\n" for line in lines))
    config_dirs = env.get("XDG_CONFIG_DIRS") or "/etc/xdg"
    return {**env, "XDG_CONFIG_DIRS": os.pathsep.join([config_dir, config_dirs])}


def uv_pinned_settings(
    env: Mapping[str, str], config_dir: str, pins: Collection[str]
) -> tuple[dict[str, str], list[str]]:
    # The environment and extra arguments for a uv command that installs `pins`.
    # Their exemption covers every version of each package, so a build
    # requirement on one (such as torch for a CUDA extension) is also held to
    # the pinned version.
    uv_env = uv_settings_env(env, config_dir, pins)
    exact_pins = _exact_pins(pins)
    if user_config_file(env) or not exact_pins:
        return uv_env, []
    build_constraints = Path(config_dir) / "build-constraints.txt"
    build_constraints.write_text("".join(f"{p}\n" for p in exact_pins.values()))
    # `--build-constraints` replaces UV_BUILD_CONSTRAINT, a list uv splits on
    # whitespace, so the user's files are passed along too.
    files = [*env.get("UV_BUILD_CONSTRAINT", "").split(), str(build_constraints)]
    return uv_env, [arg for f in files for arg in ("--build-constraints", f)]


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


def _exact_pins(requirements: Collection[str]) -> dict[str, str]:
    # Package name to its exact pin, for the requirements pinned to one version.
    pins: dict[str, str] = {}
    for requirement in requirements:
        try:
            parsed = Requirement(requirement)
        except InvalidRequirement:
            continue
        if any(
            s.operator in ("==", "===") and not s.version.endswith(".*")
            for s in parsed.specifier
        ):
            pins[canonicalize_name(parsed.name)] = f"{parsed.name}{parsed.specifier}"
    return pins


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")
