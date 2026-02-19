import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    init_output,
    parse_config_options,
)
from inspect_flow._config.load import int_load_spec
from inspect_flow._config.write import print_config_yaml


@click.command("config", help="Output config")
@config_options
def config_command(
    config_file: str,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to output config."""
    init_output(**kwargs)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    fconfig = int_load_spec(config_file, options=config_options)
    print_config_yaml(fconfig, resolved=False)
