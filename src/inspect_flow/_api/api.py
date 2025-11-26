from pathlib import Path

import click

from inspect_flow._config.load import (
    apply_auto_includes,
    apply_substitions,
    expand_includes,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import launch
from inspect_flow._types.flow_types import FlowJob


def _prepare_job(job: FlowJob, base_dir: str) -> FlowJob:
    file = str(Path(base_dir) / "unknown_file")
    job = expand_includes(
        job,
        including_job_path=file,
    )
    job = apply_auto_includes(job, config_file=file, config_options={})
    job = apply_substitions(job)
    return job


def run(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    no_venv: bool = False,
    no_prepare_job: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
        no_venv: If True, do not create a virtual environment to run the job.
        no_prepare_job: If True, do not prepare the job by expanding includes and applying substitutions before running it.
    """
    run_args = ["--dry-run"] if dry_run else []
    base_dir = base_dir or Path().cwd().as_posix()
    if not no_prepare_job:
        job = _prepare_job(job, base_dir=base_dir)
    launch(job=job, base_dir=base_dir, run_args=run_args, no_venv=no_venv)


def config(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    resolve: bool = False,
    no_venv: bool = False,
    no_prepare_job: bool = False,
) -> None:
    """Print the flow job configuration.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        resolve: If True, resolve the configuration before printing.
        no_venv: If True, do not create a virtual environment to resolve the job.
        no_prepare_job: If True, do not prepare the job by expanding includes and applying substitutions before running it.
    """
    base_dir = base_dir or Path().cwd().as_posix()
    if not no_prepare_job:
        job = _prepare_job(job, base_dir=base_dir)
    if resolve:
        launch(job=job, base_dir=base_dir, run_args=["--config"], no_venv=no_venv)
    else:
        dump = config_to_yaml(job)
        click.echo(dump)
