import os
from pathlib import Path

import click
from dotenv import dotenv_values, find_dotenv

from inspect_flow._config.load import (
    LoadState,
    after_flow_job_loaded,
    apply_auto_includes,
    apply_substitions,
    expand_includes,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import launch
from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.logging import init_flow_logging


def run(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    log_level: str | None = None,
    no_venv: bool = False,
    no_prepare_job: bool = False,
    no_dotenv: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
        log_level: The Inspect Flow log level to use. Use job.options.log_level to set the Inspect AI log level.
        no_venv: If True, do not create a virtual environment to run the job.
        no_prepare_job: If True, do not prepare the job by expanding includes and applying substitutions before running it.
        no_dotenv: If True, do not load environment variables from a .env file.
    """
    init_flow_logging(log_level)
    run_args = ["--dry-run"] if dry_run else []
    base_dir = base_dir or Path().cwd().as_posix()
    if not no_prepare_job:
        job = _prepare_job(job, base_dir=base_dir)
    launch(
        job=job,
        base_dir=base_dir,
        env=_get_env(base_dir, no_dotenv),
        run_args=run_args,
        no_venv=no_venv,
    )


def config(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    resolve: bool = False,
    log_level: str | None = None,
    no_venv: bool = False,
    no_prepare_job: bool = False,
    no_dotenv: bool = False,
) -> None:
    """Print the flow job configuration.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        resolve: If True, resolve the configuration before printing.
        log_level: The Inspect Flow log level to use. Use job.options.log_level to set the Inspect AI log level.
        no_venv: If True, do not create a virtual environment to resolve the job.
        no_prepare_job: If True, do not prepare the job by expanding includes and applying substitutions before running it.
        no_dotenv: If True, do not load environment variables from a .env file.
    """
    init_flow_logging(log_level)
    base_dir = base_dir or Path().cwd().as_posix()
    if not no_prepare_job:
        job = _prepare_job(job, base_dir=base_dir)
    if resolve:
        launch(
            job=job,
            base_dir=base_dir,
            env=_get_env(base_dir, no_dotenv),
            run_args=["--config"],
            no_venv=no_venv,
        )
    else:
        dump = config_to_yaml(job)
        click.echo(dump)


def _prepare_job(job: FlowJob, base_dir: str) -> FlowJob:
    state = LoadState()
    job = expand_includes(
        job,
        state,
        base_dir=base_dir,
    )
    job = apply_auto_includes(job, base_dir=base_dir, config_options={}, state=state)
    job = apply_substitions(job, base_dir=base_dir)
    after_flow_job_loaded(job, state)
    return job


def _get_env(base_dir: str, no_dotenv: bool) -> dict[str, str]:
    env = os.environ.copy()
    if no_dotenv:
        return env
    # Temporarily change to base_dir to find .env file
    original_cwd = os.getcwd()
    try:
        os.chdir(base_dir)
        # Already loaded environment variables should take precedence
        dotenv = dotenv_values(find_dotenv(usecwd=True))
        env = {k: v for k, v in dotenv.items() if v is not None} | env
    finally:
        os.chdir(original_cwd)
    return env
