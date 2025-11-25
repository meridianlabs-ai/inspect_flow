import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from inspect_flow import FlowJob, FlowTask
from inspect_flow._launcher.venv import create_venv
from inspect_flow._types.flow_types import FlowDependencies


def test_no_dependencies() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
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
                f"-e {flow_path}",
                "inspect_evals",
            ]


def test_auto_dependency() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            create_venv(
                job=FlowJob(
                    tasks=[
                        FlowTask(
                            name="inspect_evals/task_name",
                            model="anthropic/claude-2",
                            model_roles={"mark": "groq/somemodel"},
                        ),
                        FlowTask(
                            name="inspect_evals/task_name",
                            model="openai/gpt-4o-mini",
                            model_roles={"mark": "google/gemini-1"},
                        ),
                    ]
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
                f"-e {flow_path}",
                "anthropic",
                "google-genai",
                "groq",
                "inspect_evals",
                "openai",
            ]


def test_python_version() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
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
        requirements_path = Path("logs") / "flow_requirements.txt"
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
        requirements_path = Path("logs") / "flow_requirements.txt"
        assert requirements_path.exists()
        with open(requirements_path, "r") as f:
            requirements = f.read()
            assert requirements.find("local_eval") != -1
