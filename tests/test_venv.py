import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from botocore.client import BaseClient
from inspect_ai.util import SandboxEnvironmentSpec
from inspect_flow import FlowDependencies, FlowModel, FlowSolver, FlowSpec, FlowTask
from inspect_flow._display.run_action import RunAction
from inspect_flow._launcher.auto_dependencies import collect_auto_dependencies
from inspect_flow._launcher.freeze import _deduplicate_freeze_requirements
from inspect_flow._launcher.pip_string import _get_pip_string_with_version
from inspect_flow._launcher.venv import _create_venv, venv_launch
from rich.console import Console

_test_action = RunAction("test")


def test_no_dependencies() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            _create_venv(
                spec=FlowSpec(tasks=[FlowTask(name="task_name")]),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert len(args) == 5
            assert args[:4] == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
            ]
            # Need to handle both pip and git formats for the inspect_ai dependency
            assert "inspect-ai" in args[4] or "inspect_ai" in args[4]


def test_dependencies() -> None:
    for additional_dependencies in ["inspect_evals", ["inspect_evals"]]:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            _create_venv(
                spec=FlowSpec(
                    dependencies=FlowDependencies(
                        additional_dependencies=additional_dependencies
                    ),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args[:5] == [
                "uv",
                "pip",
                "install",
                "inspect_evals",
                f"-e {flow_path}",
            ]


def test_relative_dependency() -> None:
    base_dir = Path(__file__).parent.resolve().as_posix()
    with (
        tempfile.TemporaryDirectory() as temp_dir,
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )

        _create_venv(
            spec=FlowSpec(
                dependencies=FlowDependencies(additional_dependencies="../local_eval"),
                tasks=[FlowTask(name="task_name")],
            ),
            base_dir=base_dir,
            temp_dir=temp_dir,
            env=os.environ.copy(),
            dry_run=False,
            action=_test_action,
        )

        assert mock_run.call_count == 2
        args = mock_run.call_args.args[0]
        flow_path = str((Path(__file__).parents[1]).resolve())
        assert args[:5] == [
            "uv",
            "pip",
            "install",
            str(Path(base_dir) / ".." / "local_eval"),
            f"-e {flow_path}",
        ]


def test_auto_dependency() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            spec = FlowSpec(
                tasks=[
                    FlowTask(
                        name="inspect_evals2/task_name",
                        model="anthropic/claude-2",
                        model_roles={"mark": "groq/somemodel"},
                        sandbox="docker",  # in inspect_ai
                    ),
                    FlowTask(
                        name="inspect_evals3/task_name",
                        model="openai/gpt-4o-mini",
                        model_roles={"mark": "google/gemini-1"},
                        solver=[
                            "solver_package2/solver_name2",
                            FlowSolver(name="solver_package3/solver_name3"),
                        ],
                        sandbox=("docker", "config"),
                    ),
                    FlowTask(
                        model=FlowModel(),  # no name model
                        sandbox="unknown_sandbox",
                    ),
                    FlowTask(
                        model="no_package_model",
                        sandbox=SandboxEnvironmentSpec("docker"),
                    ),
                ]
            )
            # Add a string task to test that code path
            assert isinstance(spec.tasks, list)
            spec.tasks.append("inspect_evals1/task_name")
            # Add a string solver to test that code path
            assert isinstance(spec.tasks[0], FlowTask)
            spec.tasks[0].solver = "solver_package/solver_name"

            _create_venv(
                spec=spec,
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args[:14] == [
                "uv",
                "pip",
                "install",
                _get_pip_string_with_version("anthropic"),
                _get_pip_string_with_version("google-genai"),
                _get_pip_string_with_version("groq"),
                "inspect_evals1",
                "inspect_evals2",
                "inspect_evals3",
                _get_pip_string_with_version("openai"),
                "solver_package",
                "solver_package2",
                "solver_package3",
                f"-e {flow_path}",
            ]


def test_no_auto_dependency() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            spec = FlowSpec(
                dependencies=FlowDependencies(auto_detect_dependencies=False),
                tasks=[
                    FlowTask(
                        name="inspect_evals2/task_name",
                        model="anthropic/claude-2",
                        model_roles={"mark": "groq/somemodel"},
                        sandbox="docker",  # in inspect_ai
                    ),
                ],
            )

            _create_venv(
                spec=spec,
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args[:4] == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
            ]


def test_no_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            spec = FlowSpec(
                dependencies=FlowDependencies(dependency_file="no_file"),
                tasks=[
                    FlowTask(
                        name="inspect_evals2/task_name",
                        model="anthropic/claude-2",
                        model_roles={"mark": "groq/somemodel"},
                        sandbox="docker",  # in inspect_ai
                    ),
                ],
            )

            _create_venv(
                spec=spec,
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args[:7] == [
                "uv",
                "pip",
                "install",
                _get_pip_string_with_version("anthropic"),
                _get_pip_string_with_version("groq"),
                "inspect_evals2",
                f"-e {flow_path}",
            ]


def test_python_version() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            _create_venv(
                spec=FlowSpec(
                    python_version="3.11",
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            assert mock_run.call_count == 2
            args = mock_run.mock_calls[0].args[0]
            assert args == [
                "uv",
                "sync",
                "--no-dev",
                "--python",
                "3.11",
                "--project",
                Path.cwd().as_posix(),
                "--active",
                "--frozen",
            ]


def test_5_flow_requirements() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            _create_venv(
                spec=FlowSpec(
                    python_version="3.11",
                    log_dir=log_dir.as_posix(),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

        requirements_path = log_dir / "flow-requirements.txt"
        assert requirements_path.exists()
        with open(requirements_path, "r") as f:
            requirements = f.read()
            assert requirements == "mocked output"


def test_333_no_flow_requirements() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            _create_venv(
                spec=FlowSpec(
                    python_version="3.11",
                    log_dir=log_dir.as_posix(),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=True,
                action=_test_action,
            )

        assert mock_run.call_count == 2
        requirements_path = log_dir / "flow-requirements.txt"
        assert not requirements_path.exists()


def test_241_dependency_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        _create_venv(
            spec=FlowSpec(
                python_version="3.12",
                log_dir="logs",
                dependencies=FlowDependencies(
                    dependency_file="tests/local_eval/pyproject.toml"
                ),
                tasks=[FlowTask(name="task_name")],
            ),
            base_dir=".",
            temp_dir=temp_dir,
            env=env,
            dry_run=False,
            action=_test_action,
        )
        requirements_path = Path("logs") / "flow-requirements.txt"
        assert requirements_path.exists()
        with open(requirements_path, "r") as f:
            requirements = f.read()
            assert "local_eval" in requirements


def test_241_no_uvlock() -> None:
    # Delete uv.lock if it exists to test behavior without lockfile
    uv_lock_path = Path("tests/local_eval/uv.lock")
    uv_lock_contents: bytes | None = None
    if uv_lock_path.exists():
        uv_lock_contents = uv_lock_path.read_bytes()
        uv_lock_path.unlink()

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
            _create_venv(
                spec=FlowSpec(
                    python_version="3.13",
                    log_dir="logs",
                    dependencies=FlowDependencies(
                        dependency_file="tests/local_eval/pyproject.toml",
                    ),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=env,
                dry_run=False,
                action=_test_action,
            )
            requirements_path = Path("logs") / "flow-requirements.txt"
            assert requirements_path.exists()
            with open(requirements_path, "r") as f:
                requirements = f.read()
                assert "local_eval" in requirements
    finally:
        if uv_lock_contents is not None:
            uv_lock_path.write_bytes(uv_lock_contents)


def test_241_requirements_txt() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        _create_venv(
            spec=FlowSpec(
                python_version="3.12",
                log_dir="logs",
                dependencies=FlowDependencies(
                    dependency_file="tests/local_eval/requirements.txt",
                ),
                tasks=[FlowTask(name="task_name")],
            ),
            base_dir=".",
            temp_dir=temp_dir,
            env=env,
            dry_run=False,
            action=_test_action,
        )
        requirements_path = Path("logs") / "flow-requirements.txt"
        assert requirements_path.exists()
        with open(requirements_path, "r") as f:
            requirements = f.read()
            assert "local_eval" in requirements


def test_241_does_not_exist() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        with pytest.raises(FileNotFoundError):
            _create_venv(
                spec=FlowSpec(
                    python_version="3.11",
                    log_dir="logs",
                    dependencies=FlowDependencies(
                        dependency_file="tests/local_eval/not_there/requirements.txt",
                    ),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=env,
                dry_run=False,
                action=_test_action,
            )


def test_241_unsupported() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        with pytest.raises(subprocess.CalledProcessError):
            _create_venv(
                spec=FlowSpec(
                    python_version="3.11",
                    log_dir="logs",
                    dependencies=FlowDependencies(
                        dependency_file="tests/local_eval/flow/local_eval_flow.py",
                    ),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=env,
                dry_run=False,
                action=_test_action,
            )


def test_241_not_found() -> None:
    # Assumes no requirements.txt above the current directory
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            _create_venv(
                spec=FlowSpec(
                    dependencies=FlowDependencies(
                        dependency_file="auto",
                    ),
                    python_version="3.11",
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir="/",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            assert mock_run.call_count == 2
            args = mock_run.mock_calls[0].args[0]
            assert args == [
                "uv",
                "venv",
                "--python",
                "3.11",
            ]

            args = mock_run.mock_calls[1].args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args[:4] == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
            ]


def test_325_uv_sync_args() -> None:
    for uv_sync_args in [
        "--dev --extra 'test with space'",
        ["--dev", "--extra", "test with space"],
    ]:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="mocked output"
                )
                _create_venv(
                    spec=FlowSpec(
                        dependencies=FlowDependencies(uv_sync_args=uv_sync_args),
                        python_version="3.11",
                        tasks=[FlowTask(name="task_name")],
                    ),
                    base_dir=".",
                    temp_dir=temp_dir,
                    env=os.environ.copy(),
                    dry_run=False,
                    action=_test_action,
                )

                assert mock_run.call_count == 2
                args = mock_run.mock_calls[0].args[0]
                assert args == [
                    "uv",
                    "sync",
                    "--no-dev",
                    "--python",
                    "3.11",
                    "--project",
                    Path.cwd().as_posix(),
                    "--active",
                    "--frozen",
                    "--dev",
                    "--extra",
                    "test with space",
                ]


def test_369_flow_requirements_s3(mock_s3: BaseClient) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        _create_venv(
            spec=FlowSpec(
                log_dir="s3://test-bucket/logs",
                tasks=[FlowTask(name="task_name")],
            ),
            base_dir=".",
            temp_dir=temp_dir,
            env=env,
            dry_run=False,
            action=_test_action,
        )

        # Verify flow-requirements.txt was created in S3
        response = mock_s3.get_object(
            Bucket="test-bucket", Key="logs/flow-requirements.txt"
        )
        requirements = response["Body"].read().decode("utf-8")
        assert "inspect_flow" in requirements
        assert "--hash=sha256:" in requirements


def test_402_env_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSPECT_EVAL_MODEL", "openai/gpt-4o")

    spec = FlowSpec(tasks=["task_name"])
    dependencies = collect_auto_dependencies(spec)
    assert len(dependencies) == 1
    assert "openai" in dependencies[0]

    spec = FlowSpec(tasks=[FlowTask(name="task_name")])
    dependencies = collect_auto_dependencies(spec)
    assert len(dependencies) == 1
    assert "openai" in dependencies[0]


def test_411_deduplicate_freeze_requirements() -> None:
    # Test case 1: Duplicate git URLs with and without commit hash
    freeze_output_with_duplicates = """
inspect-ai @ git+https://github.com/UKGovernmentBEIS/inspect_ai.git@87842be92af543d1122b5d5fdf4009f3484c963e
inspect-ai @ git+https://github.com/UKGovernmentBEIS/inspect_ai.git
packaging==25.0
pydantic==2.12.5
"""
    result = _deduplicate_freeze_requirements(freeze_output_with_duplicates)
    lines = result.strip().split("\n")

    # Should only have one inspect-ai entry
    inspect_ai_lines = [line for line in lines if line.startswith("inspect-ai")]
    assert len(inspect_ai_lines) == 1
    # Should keep the one with commit hash (longer ref)
    assert "@87842be92af543d1122b5d5fdf4009f3484c963e" in inspect_ai_lines[0], (
        "Should keep the URL with commit hash"
    )

    # Should keep all other packages
    assert any(line.startswith("packaging==") for line in lines)
    assert any(line.startswith("pydantic==") for line in lines)

    # Test case 2: Duplicate with branch vs commit hash
    freeze_output_branch_vs_hash = """
my-package @ git+https://github.com/foo/bar.git@main
my-package @ git+https://github.com/foo/bar.git@abc123def456789012345678901234567890abcd
requests==2.32.5
"""
    result = _deduplicate_freeze_requirements(freeze_output_branch_vs_hash)
    lines = result.strip().split("\n")

    my_package_lines = [line for line in lines if line.startswith("my-package")]
    assert len(my_package_lines) == 1
    # Should keep the one with commit hash (longer ref)
    assert "abc123def456789012345678901234567890abcd" in my_package_lines[0]

    # Test case 3: No duplicates - should pass through unchanged
    freeze_output_no_duplicates = """
packaging==25.0
pydantic==2.12.5
requests==2.32.5
"""
    result = _deduplicate_freeze_requirements(freeze_output_no_duplicates)
    lines = result.strip().split("\n")
    assert len(lines) == 3
    assert any(line.startswith("packaging==") for line in lines)
    assert any(line.startswith("pydantic==") for line in lines)
    assert any(line.startswith("requests==") for line in lines)

    # Test case 4: Empty lines and comments should be filtered
    freeze_output_with_comments = """# This is a comment
packaging==25.0

pydantic==2.12.5
"""
    result = _deduplicate_freeze_requirements(freeze_output_with_comments)
    lines = result.strip().split("\n")
    # Should only have the two actual packages, no comments or empty lines
    assert len(lines) == 2
    assert all(not line.startswith("#") for line in lines)
    assert all(line.strip() for line in lines)

    # git overrides of pypi
    freeze_output_branch_vs_hash = """
my-package==1.0.0
my-package @ git+https://github.com/foo/bar.git@main
my-package @ git+https://github.com/foo/bar.git@abc123def456789012345678901234567890abcd
"""
    result = _deduplicate_freeze_requirements(freeze_output_branch_vs_hash)
    lines = result.strip().split("\n")

    my_package_lines = [line for line in lines if line.startswith("my-package")]
    assert len(my_package_lines) == 1
    # Should keep the one with commit hash (longer ref)
    assert "abc123def456789012345678901234567890abcd" in my_package_lines[0]

    # git overrides of pypi
    freeze_output_branch_vs_hash = """
my-package @ git+https://github.com/foo/bar.git@main
my-package @ git+https://github.com/foo/bar.git@abc123def456789012345678901234567890abcd
my-package==1.0.0
"""
    result = _deduplicate_freeze_requirements(freeze_output_branch_vs_hash)
    lines = result.strip().split("\n")

    my_package_lines = [line for line in lines if line.startswith("my-package")]
    assert len(my_package_lines) == 1
    # Should keep the one with commit hash (longer ref)
    assert "abc123def456789012345678901234567890abcd" in my_package_lines[0]


def test_pip_error(recording_console: Console) -> None:
    spec = FlowSpec(
        log_dir="logs",
        dependencies=FlowDependencies(
            additional_dependencies=["not-existing-package>=0.1.0"],
        ),
        tasks=[FlowTask(name="task_name")],
    )
    with pytest.raises(subprocess.CalledProcessError):
        venv_launch(
            spec=spec,
            base_dir=".",
            dry_run=False,
        )

    output = " ".join(recording_console.export_text().split())
    assert (
        "Because not-existing-package was not found in the package registry and you require not-existing-package>=0.1.0, we can conclude that your requirements are unsatisfiable."
        in output
    )
