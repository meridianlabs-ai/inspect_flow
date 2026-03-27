from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv
from inspect_ai._util.file import filesystem
from inspect_ai._util.path import chdir_python

from inspect_flow._config.load import (
    ConfigOptions,
    expand_spec,
    int_load_spec,
)
from inspect_flow._config.write import config_to_yaml
from inspect_flow._display.display import DisplayType, set_display_type
from inspect_flow._launcher.launch import launch, launch_check
from inspect_flow._store.store import FlowStore, store_factory
from inspect_flow._types.flow_types import FlowSpec, FlowTask
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging
from inspect_flow._util.module_util import is_loading_spec

_initialized = False


def init(
    log_level: str = DEFAULT_LOG_LEVEL,
    display: DisplayType = "full",
    dotenv_base_dir: str | None = ".",
) -> None:
    """Initialize the inspect_flow API.

    Args:
        log_level: The Inspect Flow log level to use.
        display: The display mode.
        dotenv_base_dir: Directory (or file path) to search for `.env` files.
            If a file path is given, its parent directory is used.
            `None` to skip `.env` loading. Defaults to `"."` (current working directory).
    """
    global _initialized
    _initialized = True
    init_flow_logging(log_level)
    set_display_type(display)
    if dotenv_base_dir is not None:
        if not filesystem(dotenv_base_dir).is_local():
            dotenv_base_dir = "."
        elif Path(dotenv_base_dir).is_file():
            dotenv_base_dir = str(Path(dotenv_base_dir).parent)
        with chdir_python(dotenv_base_dir):
            load_dotenv(find_dotenv(usecwd=True))


def ensure_init(dotenv_base_dir: str | None) -> None:
    if not _initialized:
        init(dotenv_base_dir=dotenv_base_dir)


def load_spec(
    file: str,
    *,
    args: dict[str, Any] | None = None,
) -> FlowSpec:
    """Load a spec from file.

    Args:
        file: The path to the spec file.
        args: A dictionary of arguments to pass as kwargs to the function in the flow config.
    """
    ensure_init(dotenv_base_dir=file)
    return int_load_spec(file=file, options=ConfigOptions(args=args or {}))


def run(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    dry_run: bool = False,
    resume: bool = False,
) -> None:
    """Run an inspect_flow evaluation.

    Args:
        spec: The flow spec configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        dry_run: If `True`, do not run eval, but show a count of tasks that would be run.
        resume: If `True`, reuse the log directory from the previous run.

    Raises:
        RuntimeError: If called from within a flow spec file being loaded.
    """
    if is_loading_spec():
        raise RuntimeError(
            "run() cannot be called from within a flow spec file. "
            "Return the FlowSpec object instead and let the CLI handle execution. "
            "Or execute the file directly using python."
        )
    ensure_init(dotenv_base_dir=base_dir)
    base_dir = base_dir or Path().cwd().as_posix()
    spec = expand_spec(spec, base_dir=base_dir, options=ConfigOptions(resume=resume))
    launch(
        spec=spec,
        base_dir=base_dir,
        dry_run=dry_run,
    )


@dataclass
class CheckTask:
    name: str  # resolved task name
    task: FlowTask  # original spec input (post-expansion)
    log_file: str | None  # path to matched log, None if no log found
    samples: int  # completed samples in log (0 if no log)
    total_samples: int | None  # expected samples (None if unknown)


@dataclass
class CheckResult:
    tasks: list[CheckTask]
    unrecognized: list[str]  # log file paths not matching any task in spec


def check(
    spec: FlowSpec,
    base_dir: str | None = None,
    *,
    log_dir: str | None = None,
) -> CheckResult | None:
    """Check completeness of an inspect_flow evaluation against existing logs.

    Args:
        spec: The flow spec configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
        log_dir: Log directory to check against. Overrides the `log_dir` in the spec.

    Returns:
        A CheckResult object containing the check results when run inproc. None when run in a venv.
    """
    ensure_init(dotenv_base_dir=base_dir)
    base_dir = base_dir or Path().cwd().as_posix()
    spec = expand_spec(
        spec,
        base_dir=base_dir,
        options=ConfigOptions(overrides=["log_dir_create_unique=False"]),
    )
    if log_dir is not None:
        spec = spec.model_copy(update={"log_dir": log_dir})
    return launch_check(spec=spec, base_dir=base_dir)


def config(
    spec: FlowSpec,
    base_dir: str | None = None,
) -> str:
    """Return the flow spec configuration.

    Args:
        spec: The flow spec configuration.
        base_dir: The base directory for resolving relative paths. Defaults to the current working directory.
    """
    ensure_init(dotenv_base_dir=base_dir)
    base_dir = base_dir or Path().cwd().as_posix()
    spec = expand_spec(spec, base_dir=base_dir)
    dump = config_to_yaml(spec)
    return dump


def store_get(store: str = "auto", create: bool = True) -> FlowStore:
    """Get a FlowStore instance.

    Args:
        store: The store location. Can be a path to the store directory or `"auto"` for the default store location.
        create: Whether to create the store if it does not exist.
    """
    ensure_init(dotenv_base_dir=".")
    flow_store = store_factory(store, base_dir=".", create=create)
    if not flow_store:
        raise ValueError(f"Could not open store at {store}")
    return flow_store
