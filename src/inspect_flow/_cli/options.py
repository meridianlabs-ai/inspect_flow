import click
from typing_extensions import TypedDict, Unpack


def config_options(f):
    """Options for overriding the config."""
    f = click.option(
        "--set",
        "-s",
        multiple=True,
        type=str,
        help="""
    Set config overrides.

    Examples:
      --set defaults.solver.args.tool_calls=none
      --set options.limit=10
      --set options.metadata={"key1": "val1", "key2": "val2"}

    The specified value may be a string or json parsable list or dict.
    If string is provided then it will be appended to existing list values.
    If json list or dict is provided then it will replace existing values.
    If the same key is provided multiple times, later values will override earlier ones.
    """,
    )(f)
    f = click.option(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of samples to run.",
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
    overrides = list(kwargs.get("set") or [])  # set may be a tuple (at least in tests)
    if flow_dir := kwargs.get("flow_dir"):
        overrides.append(f"flow_dir={flow_dir}")
    if limit := kwargs.get("limit"):
        overrides.append(f"options.limit={limit}")
    return overrides
