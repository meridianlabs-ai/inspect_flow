import click
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    options_to_overrides,
)
from inspect_flow._config.config import config, load_config


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
    fconfig = load_config(config_file, overrides=overrides)
    config(fconfig, config_file_path=config_file, resolve=resolve)
