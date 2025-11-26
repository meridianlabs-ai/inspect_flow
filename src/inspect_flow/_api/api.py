from pathlib import Path

import click

from inspect_flow._config.load import expand_includes
from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import launch
from inspect_flow._types.flow_types import FlowJob


def run(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    no_venv: bool = False,
    no_expand_includes: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
        no_venv: If True, do not create a virtual environment to run the job.
        no_expand_includes: If True, do not expand includes before running the job.
    """
    run_args = ["--dry-run"] if dry_run else []
    base_dir = base_dir or Path().cwd().as_posix()
    if not no_expand_includes:
        job = expand_includes(job, including_job_path=base_dir + "/unknown_file")
    launch(job=job, base_dir=base_dir, run_args=run_args, no_venv=no_venv)


def config(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    resolve: bool = False,
    no_venv: bool = False,
    no_expand_includes: bool = False,
) -> None:
    """Print the flow job configuration.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        resolve: If True, resolve the configuration before printing.
        no_venv: If True, do not create a virtual environment to resolve the job.
        no_expand_includes: If True, do not expand includes before running the job.
    """
    base_dir = base_dir or Path().cwd().as_posix()
    if not no_expand_includes:
        job = expand_includes(job, including_job_path=base_dir + "/unknown_file")
    if resolve:
        launch(job=job, base_dir=base_dir, run_args=["--config"], no_venv=no_venv)
    else:
        dump = config_to_yaml(job)
        click.echo(dump)
