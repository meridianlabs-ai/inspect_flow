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
from moto import mock_aws


@pytest.fixture(scope="module")
def mock_s3():
    server = ThreadedMotoServer(port=19100)
    server.start()

    # Give the server a moment to start up
    time.sleep(1)

    existing_env = {
        key: os.environ.get(key, None)
        for key in [
            "AWS_ENDPOINT_URL",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_DEFAULT_REGION",
        ]
    }

    os.environ["AWS_ENDPOINT_URL"] = "http://127.0.0.1:19100"
    os.environ["AWS_ACCESS_KEY_ID"] = "unused_id_mock_s3"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "unused_key_mock_s3"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-1"

    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket="test-bucket",
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    yield

    # Unfortunately, we can't just throw away moto after the test,
    # because there is caching of S3 bucket state (e.g. ownership)
    # somewhere in s3fs or boto. So we have to go through
    # the charade of emptying and deleting the mocked bucket.
    s3 = boto3.resource("s3")
    s3_bucket = s3.Bucket("test-bucket")
    bucket_versioning = s3.BucketVersioning("test-bucket")
    if bucket_versioning.status == "Enabled":
        s3_bucket.object_versions.delete()
    else:
        s3_bucket.objects.all().delete()

    s3_client.delete_bucket(Bucket="test-bucket")

    server.stop()
    for key, value in existing_env.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value


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
