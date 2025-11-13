import click
from typing_extensions import TypedDict, Unpack

from inspect_flow._config.load import ConfigOptions


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
        "--var",
        multiple=True,
        type=str,
        help="""
    Set variables accessible to code executing in the config file through the variable `__flow_vars__`:
    `task_min_priority = __flow_vars__.get("task_min_priority", 1)`


    Examples:
      --var task_min_priority=2

    If the same key is provided multiple times, later values will override earlier ones.
    """,
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
    var: list[str] | None


def _options_to_overrides(**kwargs: Unpack[ConfigOptionArgs]) -> list[str]:
    overrides = list(kwargs.get("set") or [])  # set may be a tuple (at least in tests)
    if flow_dir := kwargs.get("flow_dir"):
        overrides.append(f"flow_dir={flow_dir}")
    if limit := kwargs.get("limit"):
        overrides.append(f"options.limit={limit}")
    return overrides


def _options_to_flow_vars(**kwargs: Unpack[ConfigOptionArgs]) -> dict[str, str]:
    flow_vars = list(kwargs.get("var") or [])  # var may be a tuple (at least in tests)
    return {k: v for k, v in (item.split("=", 1) for item in flow_vars)}


def parse_config_options(**kwargs: Unpack[ConfigOptionArgs]) -> ConfigOptions:
    return ConfigOptions(
        overrides=_options_to_overrides(**kwargs),
        flow_vars=_options_to_flow_vars(**kwargs),
    )
