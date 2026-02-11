import yaml
from rich.rule import Rule
from rich.syntax import Syntax

from inspect_flow._types.flow_types import (
    FlowSpec,
)
from inspect_flow._util.console import flow_print
from inspect_flow._util.pydantic_util import model_dump


def config_to_yaml(spec: FlowSpec) -> str:
    return yaml.dump(
        model_dump(spec),
        default_flow_style=False,
        sort_keys=False,
    )


def print_config_yaml(spec: FlowSpec, resolved: bool) -> None:
    dump = config_to_yaml(spec)
    yaml_syntax = Syntax(dump, "yaml", theme="monokai", background_color="default")
    title = "Resolved configuration as YAML" if resolved else "Configuration as YAML"
    flow_print("", Rule(title), yaml_syntax, Rule())
