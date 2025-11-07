import click
from typing_extensions import TypedDict, Unpack


def config_options(f):
    """Options for overriding the config."""
    f = click.option(
        "--set",
        "-s",
        multiple=True,
        type=str,
        help="Set config overrides, e.g. 'defaults/solver/args/tool_calls=none'",
    )(f)
    f = click.option(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of tasks to run.",
        envvar="INSPECT_FLOW_LIMIT",
    )(f)
    f = click.option(
        "--flow-dir",
        type=str,
        default=None,
        help="Override the flow directory specified in the config.",
        envvar="INSPECT_FLOW_DIR",
    )(f)
    return f


class ConfigOptionArgs(TypedDict, total=False):
    flow_dir: str | None
    limit: int | None
    set: list[str] | None


def options_to_overrides(**kwargs: Unpack[ConfigOptionArgs]) -> list[str]:
    """Create a list of config overrides from CLI options."""
    overrides = kwargs.get("set") or []
    if flow_dir := kwargs.get("flow_dir"):
        overrides.append(f"flow_dir={flow_dir}")
    if limit := kwargs.get("limit"):
        overrides.append(f"options/limit={limit}")
    return overrides
