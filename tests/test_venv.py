import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from inspect_ai.util import SandboxEnvironmentSpec
from inspect_flow import FlowDependencies, FlowJob, FlowModel, FlowSolver, FlowTask
from inspect_flow._launcher.venv import create_venv


def test_no_dependencies() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            create_venv(
                job=FlowJob(tasks=[FlowTask(name="task_name")]),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
            ]


def test_dependencies() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            create_venv(
                job=FlowJob(
                    dependencies=FlowDependencies(
                        additional_dependencies=["inspect_evals"]
                    ),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args == [
                "uv",
                "pip",
                "install",
                "inspect_evals",
                f"-e {flow_path}",
            ]


def test_auto_dependency() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            job = FlowJob(
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
            assert isinstance(job.tasks, list)
            job.tasks.append("inspect_evals/task_name")
            # Add a string solver to test that code path
            assert isinstance(job.tasks[0], FlowTask)
            job.tasks[0].solver = "solver_package/solver_name"

            create_venv(
                job=job,
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args == [
                "uv",
                "pip",
                "install",
                "anthropic",
                "google-genai",
                "groq",
                "inspect_evals",
                "inspect_evals2",
                "inspect_evals3",
                "openai",
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
            job = FlowJob(
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

            create_venv(
                job=job,
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args == [
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
            job = FlowJob(
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

            create_venv(
                job=job,
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
            )

            assert mock_run.call_count == 2
            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args == [
                "uv",
                "pip",
                "install",
                "anthropic",
                "groq",
                "inspect_evals2",
                f"-e {flow_path}",
            ]


def test_python_version() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            create_venv(
                job=FlowJob(
                    python_version="3.11",
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
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
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            create_venv(
                job=FlowJob(
                    python_version="3.11",
                    log_dir="logs",
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
            )

        assert mock_run.call_count == 3
        args = mock_run.mock_calls[2].args[0]
        assert args == [
            "uv",
            "pip",
            "freeze",
        ]
        requirements_path = Path("logs") / "flow-requirements.txt"
        assert requirements_path.exists()
        with open(requirements_path, "r") as f:
            requirements = f.read()
            assert requirements == "mocked output"


def test_241_dependency_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        create_venv(
            job=FlowJob(
                python_version="3.11",
                log_dir="logs",
                dependencies=FlowDependencies(
                    dependency_file="tests/local_eval/pyproject.toml"
                ),
                tasks=[FlowTask(name="task_name")],
            ),
            base_dir=".",
            temp_dir=temp_dir,
            env=env,
        )
        requirements_path = Path("logs") / "flow-requirements.txt"
        assert requirements_path.exists()
        with open(requirements_path, "r") as f:
            requirements = f.read()
            assert "local_eval" in requirements


def test_241_no_uvlock() -> None:
    # Delete uv.lock if it exists to test behavior without lockfile
    uv_lock_path = Path("tests/local_eval/uv.lock")
    if uv_lock_path.exists():
        uv_lock_path.unlink()

    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        create_venv(
            job=FlowJob(
                python_version="3.11",
                log_dir="logs",
                dependencies=FlowDependencies(
                    dependency_file="tests/local_eval/pyproject.toml",
                ),
                tasks=[FlowTask(name="task_name")],
            ),
            base_dir=".",
            temp_dir=temp_dir,
            env=env,
        )
        requirements_path = Path("logs") / "flow-requirements.txt"
        assert requirements_path.exists()
        with open(requirements_path, "r") as f:
            requirements = f.read()
            assert "local_eval" in requirements


def test_241_requirements_txt() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        create_venv(
            job=FlowJob(
                python_version="3.11",
                log_dir="logs",
                dependencies=FlowDependencies(
                    dependency_file="tests/local_eval/requirements.txt",
                ),
                tasks=[FlowTask(name="task_name")],
            ),
            base_dir=".",
            temp_dir=temp_dir,
            env=env,
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
            create_venv(
                job=FlowJob(
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
            )


def test_241_unsupported() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(Path(temp_dir) / ".venv")
        with pytest.raises(subprocess.CalledProcessError):
            create_venv(
                job=FlowJob(
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
            create_venv(
                job=FlowJob(
                    dependencies=FlowDependencies(
                        dependency_file="auto",
                    ),
                    python_version="3.11",
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir="/",
                temp_dir=temp_dir,
                env=os.environ.copy(),
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
            assert args == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
            ]
