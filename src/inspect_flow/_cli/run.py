import subprocess
import sys
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
from inspect_flow._launcher.launch import launch
from inspect_flow._util.logging import init_flow_logging


@click.command("run", help="Run a job")
@click.option(
    "--dry-run",
    type=bool,
    is_flag=True,
    help="Do not run job, but show a count of tasks that would be run.",
    envvar="INSPECT_FLOW_DRY_RUN",
)
@config_options
def run_command(
    config_file: str,
    dry_run: bool,
    **kwargs: Unpack[ConfigOptionArgs],
) -> None:
    """CLI command to run a job."""
    log_level = kwargs.get("log_level")
    init_flow_logging(log_level)
    config_options = parse_config_options(**kwargs)
    config_file = absolute_file_path(config_file)
    job = int_load_job(config_file, options=config_options)
    try:
        launch(
            job,
            base_dir=str(Path(config_file).parent),
            run_args=["--dry-run"] if dry_run else [],
            no_venv=kwargs.get("no_venv", False) or False,
            no_dotenv=False,
        )
    except subprocess.CalledProcessError as e:
        # Exit on assumption that the subprocess already traced the error information
        sys.exit(e.returncode)
