from pathlib import Path
from typing import Any

from inspect_flow._config.load import (
    ConfigOptions,
    expand_job,
    int_load_job,
)
from inspect_flow._launcher.launch import launch_config, launch_run
from inspect_flow._types.flow_types import FlowJob
from inspect_flow._util.logging import init_flow_logging


def load_job(
    file: str,
    *,
    log_level: str | None = None,
    args: dict[str, Any] | None = None,
) -> FlowJob:
    """Load a job file and apply any overrides.

    Args:
        file: The path to the job configuration file.
        log_level: The Inspect Flow log level to use. Use job.options.log_level to set the Inspect AI log level.
        args: A dictionary of arguments to pass as kwargs to the function in the flow config.
    """
    init_flow_logging(log_level)
    return int_load_job(file=file, options=ConfigOptions(args=args or {}))


def run(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    log_level: str | None = None,
    no_venv: bool = False,
    no_dotenv: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
        log_level: The Inspect Flow log level to use. Use job.options.log_level to set the Inspect AI log level.
        no_venv: If True, do not create a virtual environment to run the job.
        no_dotenv: If True, do not load environment variables from a .env file.
    """
    init_flow_logging(log_level)
    base_dir = base_dir or Path().cwd().as_posix()
    job = expand_job(job, base_dir=base_dir)
    launch_run(
        job=job,
        base_dir=base_dir,
        dry_run=dry_run,
        no_venv=no_venv,
        no_dotenv=no_dotenv,
    )


def config(
    job: FlowJob,
    base_dir: str | None = None,
    *,
    resolve: bool = False,
    log_level: str | None = None,
    no_venv: bool = False,
    no_dotenv: bool = False,
) -> None:
    """Print the flow job configuration.

    Args:
        job: The flow job configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        resolve: If True, resolve the configuration before printing.
        log_level: The Inspect Flow log level to use. Use job.options.log_level to set the Inspect AI log level.
        no_venv: If True, do not create a virtual environment to resolve the job.
        no_dotenv: If True, do not load environment variables from a .env file.
    """
    init_flow_logging(log_level)
    base_dir = base_dir or Path().cwd().as_posix()
    job = expand_job(job, base_dir=base_dir)
    launch_config(
        job=job,
        base_dir=base_dir,
        resolve=resolve,
        no_venv=no_venv,
        no_dotenv=no_dotenv,
    )
