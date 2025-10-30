import click
import yaml

from inspect_flow._config.config import load_config


@click.command("config", help="Output config")
@click.argument("config-file", type=str, required=True)
def config_command(
    config_file: str,
) -> None:
    config = load_config(config_file)
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
