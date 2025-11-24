from pathlib import Path

import click

from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import launch
from inspect_flow._types.flow_types import FlowJob


def run(
    job: FlowJob,
    base_dir: str | None = None,
    dry_run: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
    """
    run_args = ["--dry-run"] if dry_run else []
    base_dir = base_dir or Path().cwd().as_posix()
    launch(job=job, base_dir=base_dir, run_args=run_args)


def config(
    job: FlowJob,
    base_dir: str | None = None,
    resolve: bool = False,
) -> None:
    """Print the flow job configuration.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        resolve: If True, resolve the configuration before printing.
    """
    if resolve:
        base_dir = base_dir or Path().cwd().as_posix()
        launch(job=job, base_dir=base_dir, run_args=["--config"])
    else:
        dump = config_to_yaml(job)
        click.echo(dump)
