import click

from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import launch
from inspect_flow._types.flow_types import FlowJob


def run(
    job: FlowJob,
    dry_run: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        job: The flow job configuration.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
    """
    run_args = ["--dry-run"] if dry_run else []
    launch(job=job, run_args=run_args)


def config(
    job: FlowJob,
    resolve: bool = False,
) -> None:
    """Print the flow job configuration.

    Args:
        job: The flow job configuration.
        resolve: If True, resolve the configuration before printing.
    """
    if resolve:
        launch(job=job, run_args=["--config"])
    else:
        dump = config_to_yaml(job)
        click.echo(dump)
