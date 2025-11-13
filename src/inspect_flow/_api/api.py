import click

from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import launch
from inspect_flow._types.flow_types import FConfig
from inspect_flow._types.generated import FlowConfig


def run(
    config: FConfig | FlowConfig,
    dry_run: bool = False,
) -> None:
    run_args = ["--dry-run"] if dry_run else []
    launch(config=config, run_args=run_args)


def config(
    config: FConfig,
    resolve: bool = False,
) -> None:
    if resolve:
        launch(config=config, run_args=["--config"])
    else:
        dump = config_to_yaml(config)
        click.echo(dump)
