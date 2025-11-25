from pathlib import Path

import click
from typing_extensions import Unpack

from inspect_flow._api.api import config
from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    parse_config_options,
)
from inspect_flow._config.load import load_job


@click.command("config", help="Output config")
@click.option(
    "--resolve",
    type=bool,
    is_flag=True,
    envvar="INSPECT_FLOW_RESOLVE",
    help="Fully resolve the config. Will create a venv and create all objects.",
)
@config_options
def config_command(
    config_file: str,
    resolve: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to output config."""
    config_options = parse_config_options(**kwargs)
    fconfig = load_job(config_file, **config_options)
    config(
        fconfig,
        base_dir=str(Path(config_file).parent),
        resolve=resolve,
        no_venv=kwargs.get("no_venv", False) or False,
    )
