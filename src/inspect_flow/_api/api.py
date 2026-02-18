from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv
from inspect_ai._util.file import dirname, filesystem
from inspect_ai._util.path import chdir_python

from inspect_flow._config.load import (
    ConfigOptions,
    expand_spec,
    int_load_spec,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._display.display import DisplayType, set_display_type
from inspect_flow._launcher.launch import launch
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.module_util import is_loading_spec


def _init_api(
    log_level: str,
    display: DisplayType,
    dotenv: bool,
    base_dir: str,
) -> None:
    init_flow_logging(log_level)
    set_display_type(display)
    if dotenv:
        dotenv_dir = base_dir if filesystem(base_dir).is_local() else "."
        with chdir_python(dotenv_dir):
            load_dotenv(find_dotenv(usecwd=True))


def load_spec(
    file: str,
    *,
    log_level: str = DEFAULT_LOG_LEVEL,
    display: DisplayType = "full",
    dotenv: bool = True,
    args: dict[str, Any] | None = None,
) -> FlowSpec:
    """Load a spec from file.

    Args:
        file: The path to the spec file.
        log_level: The Inspect Flow log level to use. Use spec.options.log_level to set the Inspect AI log level.
        display: The display mode.
        dotenv: If True, load environment variables from a .env file.
        args: A dictionary of arguments to pass as kwargs to the function in the flow config.
    """
    _init_api(
        log_level=log_level,
        display=display,
        dotenv=dotenv,
        base_dir=dirname(file) or ".",
    )
    return int_load_spec(file=file, options=ConfigOptions(args=args or {}))


def run(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    log_level: str = DEFAULT_LOG_LEVEL,
    display: DisplayType = "full",
    dotenv: bool = True,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        spec: The flow spec configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If True, do not run eval, but show a count of tasks that would be run.
        log_level: The Inspect Flow log level to use. Use spec.options.log_level to set the Inspect AI log level.
        display: The display mode.
        dotenv: If True, load environment variables from a .env file.

    Raises:
        RuntimeError: If called from within a flow spec file being loaded.
    """
    if is_loading_spec():
        raise RuntimeError(
            "run() cannot be called from within a flow spec file. "
            "Return the FlowSpec object instead and let the CLI handle execution. "
            "Or execute the file directly using python."
        )
    base_dir = base_dir or Path().cwd().as_posix()
    _init_api(log_level=log_level, display=display, dotenv=dotenv, base_dir=base_dir)
    spec = expand_spec(spec, base_dir=base_dir)
    launch(
        spec=spec,
        base_dir=base_dir,
        dry_run=dry_run,
    )


def config(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    log_level: str = DEFAULT_LOG_LEVEL,
    display: DisplayType = "full",
    dotenv: bool = True,
) -> str:
    """Return the flow spec configuration.

    Args:
        spec: The flow spec configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        log_level: The Inspect Flow log level to use. Use spec.options.log_level to set the Inspect AI log level.
        display: The display mode.
        dotenv: If True, load environment variables from a .env file.
    """
    base_dir = base_dir or Path().cwd().as_posix()
    _init_api(log_level=log_level, display=display, dotenv=dotenv, base_dir=base_dir)
    spec = expand_spec(spec, base_dir=base_dir)
    dump = config_to_yaml(spec)
    return dump


def store_get(
    store: str = "auto",
    create: bool = True,
    *,
    log_level: str = DEFAULT_LOG_LEVEL,
    display: DisplayType = "full",
    dotenv: bool = True,
) -> FlowStore:
    """Get a FlowStore instance.

    Args:
        store: The store location. Can be a path to the store directory or "auto" for the default store location.
        create: Whether to create the store if it does not exist.
        log_level: The Inspect Flow log level to use.
        display: The display mode.
        dotenv: If True, load environment variables from a .env file.
    """
    _init_api(log_level=log_level, display=display, dotenv=dotenv, base_dir=".")
    flow_store = store_factory(store, base_dir=".", create=create)
    if not flow_store:
        raise ValueError(f"Could not open store at {store}")
    return flow_store
