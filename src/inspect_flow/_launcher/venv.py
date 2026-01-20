import shlex
import sys
from logging import getLogger
from pathlib import Path
from typing import List, Literal, Sequence

from inspect_ai._util.file import file, filesystem

from inspect_flow._launcher.auto_dependencies import collect_auto_dependencies
from inspect_flow._launcher.pip_string import get_pip_string
from inspect_flow._launcher.python_version import resolve_python_version
from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.path_util import absolute_path_relative_to
from inspect_flow._util.subprocess_util import run_with_logging

logger = getLogger(__name__)


def create_venv(
    spec: FlowSpec,
    base_dir: str,
    temp_dir: str,
    env: dict[str, str],
    dry_run: bool = False,
) -> None:
    _create_venv_with_base_dependencies(
        spec, base_dir=base_dir, temp_dir=temp_dir, env=env
    )

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

    _uv_pip_install(dependencies, temp_dir, env)

    # Freeze installed packages to flow-requirements.txt in log_dir
    if not dry_run and spec.log_dir:
        freeze_result = run_with_logging(
            ["uv", "pip", "freeze"],
            cwd=temp_dir,
            env=env,
            log_output=False,  # Don't log the full freeze output
        )
        # Deduplicate freeze output to avoid conflicting URLs
        deduplicated_freeze = _deduplicate_freeze_requirements(freeze_result.stdout)

        requirements_in = Path(temp_dir) / "flow-requirements.in"
        with open(requirements_in, "w") as f:
            f.write(deduplicated_freeze)

        compile_result = run_with_logging(
            [
                "uv",
                "pip",
                "compile",
                "--generate-hashes",
                "--no-header",
                "--no-annotate",
                str(requirements_in),
            ],
            cwd=temp_dir,
            env=env,
            log_output=False,
        )

        fs = filesystem(spec.log_dir)
        fs.mkdir(spec.log_dir, exist_ok=True)
        with file(spec.log_dir + "/flow-requirements.txt", "w") as f:
            f.write(compile_result.stdout)


def _resolve_dependency(dependency: str, base_dir: str) -> str:
    if "/" in dependency:
        return absolute_path_relative_to(dependency, base_dir=base_dir)
    return dependency


def _create_venv_with_base_dependencies(
    spec: FlowSpec, base_dir: str, temp_dir: str, env: dict[str, str]
) -> None:
    file_type: Literal["requirements.txt", "pyproject.toml"] | None = None
    file_path: str | None = None
    dependency_file_info = _get_dependency_file(spec, base_dir=base_dir)
    if not dependency_file_info:
        logger.info("No dependency file found, creating bare venv")
        _uv_venv(spec, temp_dir, env)
        return

    file_type, file_path = dependency_file_info
    if file_type == "requirements.txt":
        logger.info(f"Using requirements.txt to create venv. File: {file_path}")
        _uv_venv(spec, temp_dir, env)
        # Need to run in the directory containing the requirements.txt to handle relative paths
        _uv_pip_install(["-r", file_path], Path(file_path).parent.as_posix(), env)
        return

    logger.info(f"Using pyproject.toml to create venv. File: {file_path}")
    project_dir = Path(file_path).parent
    if not spec.python_version:
        spec.python_version = resolve_python_version(file_path)

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

    logger.info(f"Creating venv with uv args: {uv_args}")
    run_with_logging(
        ["uv", "sync"] + uv_args,
        cwd=temp_dir,
        env=env,
    )


def _uv_sync_args(spec: FlowSpec) -> Sequence[str]:
    if spec.dependencies and spec.dependencies.uv_sync_args:
        if isinstance(spec.dependencies.uv_sync_args, str):
            return shlex.split(spec.dependencies.uv_sync_args)
        else:
            return spec.dependencies.uv_sync_args
    return []


def _uv_venv(spec: FlowSpec, temp_dir: str, env: dict[str, str]) -> None:
    spec.python_version = (
        spec.python_version
        or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

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


def _deduplicate_freeze_requirements(freeze_output: str) -> str:
    """Deduplicate package entries in freeze output, keeping the most specific URL."""
    lines = freeze_output.strip().split("\n")
    packages: dict[str, str] = {}

    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue

        # Extract package name (handle both regular and URL-based packages)
        # Format: "package==version" or "package @ url"
        package_name = line.split("==")[0].split(" @ ")[0].strip()

        if package_name not in packages:
            packages[package_name] = line
        else:
            existing = packages[package_name]
            # Check if either line has a git URL with commit hash (@<hash>)
            # Prefer: git+...@<commit_hash> over git+...@<branch> over git+...
            if " @ git+" in line and " @ git+" in existing:
                # Both are git URLs, prefer the one with what looks like a commit hash
                # Commit hashes are typically 40 chars, branches are shorter
                line_ref = (
                    line.split("@")[-1] if "@" in line.split(" @ git+")[-1] else ""
                )
                existing_ref = (
                    existing.split("@")[-1]
                    if "@" in existing.split(" @ git+")[-1]
                    else ""
                )

                if len(line_ref) > len(existing_ref):
                    packages[package_name] = line
            elif " @ git+" in line:
                # New line is git URL, existing is not - prefer git URL
                packages[package_name] = line

    return "\n".join(packages.values()) + "\n"
