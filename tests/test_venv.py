from platform import python_version
import tempfile
from pathlib import Path
from unittest.mock import patch

from inspect_flow._submit.venv import create_venv
from inspect_flow._types.flow_types import FlowConfig


def test_no_dependencies() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            create_venv(
                config=FlowConfig(matrix=[{"tasks": ["task_name"]}]), temp_dir=temp_dir
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
                config=FlowConfig(
                    dependencies=["inspect_evals"], matrix=[{"tasks": ["task_name"]}]
                ),
                temp_dir=temp_dir,
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


def test_model_dependency() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            create_venv(
                config=FlowConfig(
                    matrix=[
                        {
                            "tasks": [
                                {
                                    "name": "task_name",
                                    "models": ["anthropic/claude-2"],
                                    "model_roles": [{"mark": "groq/somemodel"}],
                                }
                            ],
                            "models": ["openai/gpt-4o-mini"],
                            "model_roles": [{"mark": {"name": "google/gemini-1"}}],
                        }
                    ],
                ),
                temp_dir=temp_dir,
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
                "openai",
            ]


def test_python_version() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            create_venv(
                config=FlowConfig(
                    python_version="3.11", matrix=[{"tasks": ["task_name"]}]
                ),
                temp_dir=temp_dir,
            )

            assert mock_run.call_count == 2
            args = mock_run.mock_calls[0].args[0]
            assert args == [
                "uv",
                "venv",
                "--python",
                "3.11",
            ]
