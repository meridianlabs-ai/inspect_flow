from pathlib import Path

import click
from inspect_ai._util.file import absolute_file_path
from typing_extensions import Unpack

from inspect_flow._cli.options import (
    ConfigOptionArgs,
    config_options,
    parse_config_options,
)
from inspect_flow._config.load import int_load_job
from inspect_flow._launcher.launch import launch_config
from inspect_flow._util.logging import init_flow_logging


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
    log_level = kwargs.get("log_level")
    init_flow_logging(log_level)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    fconfig = int_load_job(config_file, options=config_options)
    launch_config(
        fconfig,
        base_dir=str(Path(config_file).parent),
        resolve=resolve,
        no_venv=kwargs.get("no_venv", False) or False,
        no_dotenv=False,
    )
