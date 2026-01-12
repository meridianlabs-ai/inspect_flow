# Configure environment BEFORE any imports that might initialize Rich
# This prevents Rich from wrapping log output at narrow column widths
import os

os.environ["COLUMNS"] = "500"
os.environ["NO_COLOR"] = "1"

import importlib.util
import subprocess
from typing import Any, Callable, TypeVar, cast

import boto3
import pytest
from moto.server import ThreadedMotoServer


@pytest.fixture(scope="session")
def moto_server():
    """Start moto server once for entire test session."""
    server = ThreadedMotoServer(port=19100)
    server.start()

    os.environ["AWS_ENDPOINT_URL"] = "http://127.0.0.1:19100"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

    yield server

    server.stop()


@pytest.fixture(scope="function")
def mock_s3(moto_server):
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
