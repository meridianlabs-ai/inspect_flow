import os
import shlex
import subprocess
import sys
import tempfile
from logging import getLogger
from pathlib import Path
from typing import Callable, List, Literal, Sequence

from inspect_ai import Task
from inspect_ai._util.file import absolute_file_path
from inspect_ai.model import Model
from inspect_ai.scorer import Scorer

from inspect_flow._config.write import write_config_file
from inspect_flow._display.display import display, get_display_type
from inspect_flow._display.run_action import RunAction
from inspect_flow._launcher.auto_dependencies import collect_auto_dependencies
from inspect_flow._launcher.freeze import write_flow_requirements
from inspect_flow._launcher.pip_string import get_pip_string
from inspect_flow._launcher.python_version import resolve_python_version
from inspect_flow._runner.cli import CHECK_ACTIONS, RUN_ACTIONS
from inspect_flow._types.flow_types import FlowAgent, FlowSolver, FlowSpec, FlowTask
from inspect_flow._util.console import path
from inspect_flow._util.logging import get_last_log_level
from inspect_flow._util.path_util import absolute_path_relative_to
from inspect_flow._util.subprocess_util import (
    CHILD_READY_FD_ENV,
    PARENT_ACK_FD_ENV,
    run_with_logging,
)

logger = getLogger(__name__)


def venv_launch(spec: FlowSpec, base_dir: str, dry_run: bool) -> None:
    _venv_spawn(spec, base_dir=base_dir, subcommand="run", dry_run=dry_run)


def venv_check(spec: FlowSpec, base_dir: str) -> None:
    _venv_spawn(spec, base_dir=base_dir, subcommand="check", dry_run=True)


def _venv_spawn(spec: FlowSpec, base_dir: str, subcommand: str, dry_run: bool) -> None:
    action_keys = (
        list(RUN_ACTIONS.keys()) if subcommand == "run" else list(CHECK_ACTIONS.keys())
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        with RunAction("env", info="venv") as action:
            _check_spec_for_venv(spec)
            run_path = (Path(__file__).parents[1] / "_runner" / "cli.py").absolute()
            base_dir = absolute_file_path(base_dir)
            run_args = ["--dry-run"] if dry_run and subcommand == "run" else []
            args = [
                "--base-dir",
                base_dir,
                "--log-level",
                get_last_log_level(),
                "--display",
                get_display_type(),
            ] + run_args

            env = os.environ.copy()
            if spec.env:
                env.update(**spec.env)

            # Set the virtual environment so that it will be created in the temp directory
            env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")

            _create_venv(
                base_dir=base_dir,
                spec=spec,
                temp_dir=temp_dir,
                env=env,
                dry_run=dry_run,
                action=action,
            )

            action.update(info="venv created")

            python_path = Path(temp_dir) / ".venv" / "bin" / "python"
            file = write_config_file(spec)

            action.update(
                info="Created venv and started flow process", status="success"
            )

        # Stop the parent display so the child inherits real terminal fds
        display().stop(remove_actions=action_keys)

        # Create pipes for bidirectional signaling with child process
        child_ready_r, child_ready_w = os.pipe()
        parent_ack_r, parent_ack_w = os.pipe()

        # Pass fd numbers to child via environment variables
        env[CHILD_READY_FD_ENV] = str(child_ready_w)
        env[PARENT_ACK_FD_ENV] = str(parent_ack_r)

        process = subprocess.Popen(
            [str(python_path), str(run_path), subcommand, "--file", file, *args],
            env=env,
            pass_fds=(child_ready_w, parent_ack_r),
        )

        # Close the ends we don't use in parent
        os.close(child_ready_w)
        os.close(parent_ack_r)

        # Wait for child to signal ready
        bytes = os.read(child_ready_r, 1)
        assert bytes == b"r", f"parent got bytes {bytes} instead of b'r'"
        os.close(child_ready_r)

        # Signal child to continue
        os.write(parent_ack_w, b"g")
        os.close(parent_ack_w)

        # Wait for process to complete (must stay inside TemporaryDirectory context
        # so the venv remains on disk while the subprocess is running)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                returncode=process.returncode,
                cmd=process.args,
            )


def _check_spec_for_venv(spec: FlowSpec) -> None:
    for task in spec.tasks or []:
        if isinstance(task, Task):
            raise ValueError(
                "In venv execution, Inspect Flow resolves tasks via the registry so they can be recreated inside the virtualenv process. You provided an already-instantiated Task object, which can not be serialized/recreated. Fix: use FlowTask instead of Task or run using 'inproc' execution type."
            )
        if isinstance(task, FlowTask):
            if isinstance(task.model, Model):
                raise ValueError(
                    "In venv execution, Inspect Flow resolves models via the registry so they can be recreated inside the virtualenv process. You provided an already-instantiated Model object in a FlowTask, which can not be serialized/recreated. Fix: use FlowModel or run using 'inproc' execution type."
                )
            if isinstance(task.scorer, Scorer):
                raise ValueError(
                    "In venv execution, Inspect Flow resolves scorers via the registry so they can be recreated inside the virtualenv process. You provided an already-instantiated Scorer object in a FlowTask, which can not be serialized/recreated. Fix: use FlowScorer or run using 'inproc' execution type."
                )
            if task.solver:
                solver_list = (
                    task.solver
                    if isinstance(task.solver, Sequence)
                    and not isinstance(task.solver, str)
                    else [task.solver]
                )
                for solver in solver_list:
                    if not isinstance(solver, (str, FlowSolver, FlowAgent)):
                        raise ValueError(
                            "In venv execution, Inspect Flow resolves solvers and agents via the registry so they can be recreated inside the virtualenv process. You provided an already-instantiated Solver or Agent object as a solver in a FlowTask, which can not be serialized/recreated. Fix: use FlowSolver or FlowAgent instead or run using 'inproc' execution type."
                        )


def _create_venv(
    spec: FlowSpec,
    base_dir: str,
    temp_dir: str,
    env: dict[str, str],
    dry_run: bool,
    action: RunAction,
) -> None:
    create_venv_func = _get_create_venv_with_base_dependencies(
        spec, base_dir=base_dir, temp_dir=temp_dir, env=env, action=action
    )

    create_venv_func()

    dependencies: List[str] = []
    if spec.dependencies and spec.dependencies.additional_dependencies:
        if isinstance(spec.dependencies.additional_dependencies, str):
            dependencies.append(spec.dependencies.additional_dependencies)
        else:
            dependencies.extend(spec.dependencies.additional_dependencies)
        dependencies = [
            _resolve_dependency(dep, base_dir=base_dir) for dep in dependencies
        ]

    auto_detect_dependencies = True
    if spec.dependencies and spec.dependencies.auto_detect_dependencies is False:
        auto_detect_dependencies = False

    if auto_detect_dependencies:
        dependencies.extend(collect_auto_dependencies(spec))
    dependencies.append(get_pip_string("inspect-flow"))
    # Ensure same version of inspect-ai is installed (supports -e installs)
    dependencies.append(get_pip_string("inspect-ai"))

    _uv_pip_install(dependencies, temp_dir, env)

    write_flow_requirements(spec, temp_dir, env, dry_run)


def _resolve_dependency(dependency: str, base_dir: str) -> str:
    if "://" in dependency or dependency.startswith(("git+", "hg+", "bzr+", "svn+")):
        return dependency
    if "/" in dependency:
        return absolute_path_relative_to(dependency, base_dir=base_dir)
    return dependency


def _get_create_venv_with_base_dependencies(
    spec: FlowSpec, base_dir: str, temp_dir: str, env: dict[str, str], action: RunAction
) -> Callable[..., None]:
    file_type: Literal["requirements.txt", "pyproject.toml"] | None = None
    file_path: str | None = None
    dependency_file_info = _get_dependency_file(spec, base_dir=base_dir)
    if not dependency_file_info:
        action.print("Dependency file: none")

        def create_venv_func() -> None:
            return _uv_venv(spec, temp_dir, env, action)

        return create_venv_func

    file_type, file_path = dependency_file_info
    action.print("Dependency file:", path(file_path))
    if file_type == "requirements.txt":

        def create_venv_func() -> None:
            _uv_venv(spec, temp_dir, env, action)
            # Need to run in the directory containing the requirements.txt to handle relative paths
            _uv_pip_install(["-r", file_path], Path(file_path).parent.as_posix(), env)

        return create_venv_func

    project_dir = Path(file_path).parent
    if not spec.python_version:
        spec.python_version = resolve_python_version(file_path)
    action.print(f"Python: {spec.python_version}")

    uv_args = [
        "--no-dev",
        "--python",
        spec.python_version,
        "--project",
        str(project_dir),
        "--active",
    ]
    if (project_dir / "uv.lock").exists():
        uv_args.append("--frozen")

    uv_args.extend(_uv_sync_args(spec))

    def create_venv_func() -> None:
        run_with_logging(
            ["uv", "sync"] + uv_args,
            cwd=temp_dir,
            env=env,
        )

    return create_venv_func


def _uv_sync_args(spec: FlowSpec) -> Sequence[str]:
    if spec.dependencies and spec.dependencies.uv_sync_args:
        if isinstance(spec.dependencies.uv_sync_args, str):
            return shlex.split(spec.dependencies.uv_sync_args)
        else:
            return spec.dependencies.uv_sync_args
    return []


def _uv_venv(
    spec: FlowSpec, temp_dir: str, env: dict[str, str], action: RunAction
) -> None:
    spec.python_version = (
        spec.python_version
        or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    action.print(f"Python: {spec.python_version}")

    run_with_logging(
        ["uv", "venv", "--python", spec.python_version],
        cwd=temp_dir,
        env=env,
    )


def _uv_pip_install(args: List[str], temp_dir: str, env: dict[str, str]) -> None:
    """Install packages using 'uv pip install'."""
    run_with_logging(
        ["uv", "pip", "install"] + args,
        cwd=temp_dir,
        env=env,
    )


def _get_dependency_file(
    spec: FlowSpec, base_dir: str
) -> tuple[Literal["requirements.txt", "pyproject.toml"], str] | None:
    if spec.dependencies and spec.dependencies.dependency_file == "no_file":
        return None

    if (
        not spec.dependencies
        or not spec.dependencies.dependency_file
        or spec.dependencies.dependency_file == "auto"
    ):
        return _search_dependency_file(base_dir=base_dir)

    file = absolute_path_relative_to(
        spec.dependencies.dependency_file, base_dir=base_dir
    )
    if not Path(file).exists():
        raise FileNotFoundError(f"Dependency file '{file}' does not exist.")
    if file.endswith("pyproject.toml"):
        return "pyproject.toml", file
    return "requirements.txt", file


def _search_dependency_file(
    base_dir: str,
) -> tuple[Literal["requirements.txt", "pyproject.toml"], str] | None:
    files: list[Literal["pyproject.toml", "requirements.txt"]] = [
        "pyproject.toml",
        "requirements.txt",
    ]

    # Walk up the directory tree starting from base_dir
    current_dir = Path(base_dir).resolve()
    found_file = None
    found_path = None
    while True:
        for file_name in files:
            file_path = current_dir / file_name
            if file_path.exists():
                if not found_file:
                    found_file = file_name
                    found_path = str(file_path)
                else:
                    logger.warning(
                        f"Multiple dependency files found when auto-detecting dependencies. "
                        f"Using '{found_file}' at '{found_path}' and ignoring "
                        f"'{file_name}' at '{file_path}'."
                    )

        # Move to parent directory
        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent
    return (found_file, found_path) if found_file and found_path else None
