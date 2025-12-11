import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._config.write import config_to_yaml
from inspect_flow._util.logging import init_flow_logging


@click.command("config", help="Output config")
@config_options
def config_command(
    config_file: str,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to output config."""
    log_level = kwargs.get("log_level")
    init_flow_logging(log_level)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    fconfig = int_load_spec(config_file, options=config_options)
    dump = config_to_yaml(fconfig)
    click.echo(dump)
