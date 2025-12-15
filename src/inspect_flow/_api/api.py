from pathlib import Path
from typing import Any

from inspect_flow._config.load import (
    ConfigOptions,
    expand_spec,
    int_load_spec,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._launcher.launch import launch
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.logging import init_flow_logging


def load_spec(
    file: str,
    *,
    log_level: str | None = None,
    args: dict[str, Any] | None = None,
) -> FlowSpec:
    """Load a spec from file.

    Args:
        file: The path to the spec file.
        log_level: The Inspect Flow log level to use. Use spec.options.log_level to set the Inspect AI log level.
        args: A dictionary of arguments to pass as kwargs to the function in the flow config.
    """
    init_flow_logging(log_level)
    return int_load_spec(file=file, options=ConfigOptions(args=args or {}))


def run(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    log_level: str | None = None,
    no_venv: bool = False,
    no_dotenv: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        spec: The flow spec configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
        log_level: The Inspect Flow log level to use. Use spec.options.log_level to set the Inspect AI log level.
        no_venv: If True, do not create a virtual environment to run the spec.
        no_dotenv: If True, do not load environment variables from a .env file.
    """
    init_flow_logging(log_level)
    base_dir = base_dir or Path().cwd().as_posix()
    spec = expand_spec(spec, base_dir=base_dir)
    launch(
        spec=spec,
        base_dir=base_dir,
        dry_run=dry_run,
        no_venv=no_venv,
        no_dotenv=no_dotenv,
    )


def config(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    log_level: str | None = None,
) -> str:
    """Return the flow spec configuration.

    Args:
        spec: The flow spec configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        log_level: The Inspect Flow log level to use. Use spec.options.log_level to set the Inspect AI log level.
    """
    init_flow_logging(log_level)
    base_dir = base_dir or Path().cwd().as_posix()
    spec = expand_spec(spec, base_dir=base_dir)
    dump = config_to_yaml(spec)
    return dump
