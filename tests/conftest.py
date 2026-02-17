# Configure environment BEFORE any imports that might initialize Rich
# This prevents Rich from wrapping log output at narrow column widths
import os

os.environ["COLUMNS"] = "500"
os.environ["NO_COLOR"] = "1"

import importlib.util
import inspect
import subprocess
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar, cast
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.client import BaseClient
from inspect_ai._util.logger import LogHandlerVar
from inspect_flow._util.constants import DEFAULT_LOG_LEVEL
from inspect_flow._util.logging import init_flow_logging
from rich.console import Console


def mock_call_arg(
    func: Callable[..., Any], mock: MagicMock, name: str, call_index: int = 0
) -> Any:
    """Get a mock call argument by parameter name, regardless of how it was passed."""
    call = mock.call_args_list[call_index]
    bound = inspect.signature(func).bind(*call.args, **call.kwargs)
    return bound.arguments[name]


@pytest.fixture(autouse=True)
def init_log_handler() -> None:
    log_handler: LogHandlerVar = {"handler": None}
    init_flow_logging(log_level=DEFAULT_LOG_LEVEL, log_handler_var=log_handler)


@pytest.fixture(autouse=True)
def isolate_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests never touch real user store."""
    monkeypatch.setattr(
        "inspect_flow._store.store._get_default_store_dir",
        lambda: tmp_path / "test_store",
    )


class MotoServer:
    """Moto S3 mock running in a separate process (avoids GIL deadlocks with Rust HTTP clients)."""

    def __init__(self) -> None:
        import socket
        import time
        import urllib.request

        with socket.socket() as sock:
            sock.bind(("", 0))
            port = sock.getsockname()[1]

        self._proc = subprocess.Popen(
            ["moto_server", "-p", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.url = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                urllib.request.urlopen(self.url, timeout=0.5)
                break
            except Exception:
                time.sleep(0.1)

    def stop(self) -> None:
        self._proc.terminate()
        self._proc.wait()


@pytest.fixture(scope="session")
def moto_server() -> Generator[MotoServer, None, None]:
    server = MotoServer()

    os.environ["AWS_ENDPOINT_URL"] = server.url
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    yield server

    server.stop()


@pytest.fixture(scope="function")
def mock_s3(moto_server: MotoServer) -> Generator[BaseClient, None, None]:
    """Create and cleanup bucket for each test."""
    s3_client = boto3.client("s3")
    s3_client.create_bucket(Bucket="test-bucket")

    yield s3_client

    # Cleanup after each test
    response = s3_client.list_objects_v2(Bucket="test-bucket")
    if "Contents" in response:
        objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
        s3_client.delete_objects(Bucket="test-bucket", Delete={"Objects": objects})
    s3_client.delete_bucket(Bucket="test-bucket")


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--runapi", action="store_true", default=False, help="run API tests"
    )
    parser.addoption(
        "--runflaky", action="store_true", default=False, help="run flaky tests"
    )


def pytest_configure(config: pytest.Config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "api: mark test as requiring API access")
    config.addinivalue_line("markers", "flaky: mark test as flaky/unreliable")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="need --runslow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    if not config.getoption("--runapi"):
        skip_api = pytest.mark.skip(reason="need --runapi option to run")
        for item in items:
            if "api" in item.keywords:
                item.add_marker(skip_api)

    if not config.getoption("--runflaky"):
        skip_flaky = pytest.mark.skip(reason="need --runflaky option to run")
        for item in items:
            if "flaky" in item.keywords:
                item.add_marker(skip_flaky)


def skip_if_env_var(var: str, exists: bool = True):
    """
    Pytest mark to skip the test if the var environment variable is not defined.

    Use in combination with `pytest.mark.api` if the environment variable in
    question corresponds to a paid API. For example, see `skip_if_no_openai`.
    """
    condition = (var in os.environ.keys()) if exists else (var not in os.environ.keys())
    return pytest.mark.skipif(
        condition,
        reason=f"Test doesn't work without {var} environment variable defined.",
    )


F = TypeVar("F", bound=Callable[..., Any])


def skip_if_no_openai(func: F) -> F:
    return cast(
        F,
        pytest.mark.api(
            pytest.mark.skipif(
                importlib.util.find_spec("openai") is None
                or os.environ.get("OPENAI_API_KEY") is None,
                reason="Test requires both OpenAI package and OPENAI_API_KEY environment variable",
            )(func)
        ),
    )


def skip_if_no_anthropic(func: F) -> F:
    return cast(
        F, pytest.mark.api(skip_if_env_var("ANTHROPIC_API_KEY", exists=False)(func))
    )


def skip_if_github_action(func: F) -> F:
    return cast(F, skip_if_env_var("GITHUB_ACTIONS", exists=True)(func))


def skip_if_no_docker(func: F) -> F:
    try:
        is_docker_installed = (
            subprocess.run(
                ["docker", "--version"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).returncode
            == 0
        )
    except FileNotFoundError:
        is_docker_installed = False

    return cast(
        F,
        pytest.mark.skipif(
            not is_docker_installed,
            reason="Test doesn't work without Docker installed.",
        )(func),
    )


@pytest.fixture
def mock_eval_set() -> Generator[MagicMock, None, None]:
    """Mock eval_set with a valid return value for tests that don't run real evaluations."""
    with patch("inspect_flow._runner.run.eval_set") as mock:
        mock.return_value = (True, [])
        yield mock


@pytest.fixture
def recording_console() -> Generator[Console, None, None]:
    """Fixture that replaces the global Rich console with a recording console.

    Use `recording_console.export_text()` to get the captured output.
    """
    recording = Console(record=True, force_terminal=True)
    with (
        patch("inspect_flow._util.console.console", recording),
        patch("inspect_flow._display.full.console", recording),
        patch("inspect_flow._display.full_actions.console", recording),
        patch("inspect_flow._cli.store.console", recording),
    ):
        yield recording


@dataclass
class MockVenvSubprocess:
    """Container for venv subprocess mocks."""

    run: MagicMock
    """Mock for subprocess.run (used for venv setup commands like uv sync, pip install)."""

    popen: MagicMock
    """Mock for subprocess.Popen (used for launching the Python process)."""


@pytest.fixture
def mock_venv_subprocess() -> Generator[MockVenvSubprocess, None, None]:
    """Mock subprocess.run and subprocess.Popen for venv launch tests.

    Also mocks os.read to handle the parent-child synchronization pipes.
    """
    import subprocess

    def mock_os_read(fd: int, n: int) -> bytes:  # noqa: ARG001
        # Return the expected synchronization byte for the child_ready pipe
        # The code expects b"r" from the child process
        return b"r"

    with (
        patch("subprocess.run") as mock_run,
        patch("subprocess.Popen") as mock_popen,
        patch("os.read", side_effect=mock_os_read),
        patch("os.write"),
        patch("os.close"),
        patch("os.pipe", return_value=(10, 11)),  # Return fake file descriptors
    ):
        # Configure subprocess.run to return success
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )

        # Configure subprocess.Popen to return a mock process
        mock_process = MagicMock()
        mock_process.wait.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        yield MockVenvSubprocess(run=mock_run, popen=mock_popen)
