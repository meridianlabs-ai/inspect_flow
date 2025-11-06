import click
import yaml

from inspect_flow._config.config import load_config
from inspect_flow._submit.submit import submit


@click.command("config", help="Output config")
@click.argument("config-file", type=str, required=True)
@click.option(
    "--resolve",
    type=bool,
    is_flag=True,
    help="Fully resolve the config. Will create a venv and create all objects.",
)
def config_command(
    config_file: str,
    resolve: bool,
) -> None:
    config = load_config(config_file)
    if resolve:
        submit(config, config_file, ["--config"])
    else:
        dump = yaml.dump(
            config.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_defaults=True,
                exclude_none=True,
            ),
            default_flow_style=False,
            sort_keys=False,
        )
        click.echo(dump)
