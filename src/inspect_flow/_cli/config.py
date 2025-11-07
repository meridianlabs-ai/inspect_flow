import click
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    options_to_overrides,
)
from inspect_flow._config.config import load_config
from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import submit


@click.command("config", help="Output config")
@click.argument("config-file", type=str, required=True)
@click.option(
    "--resolve",
    type=bool,
    is_flag=True,
    help="Fully resolve the config. Will create a venv and create all objects.",
)
@config_options
def config_command(
    config_file: str,
    resolve: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    overrides = options_to_overrides(**kwargs)
    config = load_config(config_file, overrides=overrides)
    if resolve:
        submit(config, config_file, ["--config"])
    else:
        dump = config_to_yaml(config)
        click.echo(dump)
