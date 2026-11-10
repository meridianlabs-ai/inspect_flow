import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import unquote

import inspect_ai.model._providers.providers  # noqa: F401  registers @modelapi providers
import pytest
from botocore.client import BaseClient
from inspect_ai import ScannerConfig
from inspect_ai._util.module import load_module
from inspect_ai._util.registry import registry_find, registry_info
from inspect_ai.model import GenerateConfig, get_model
from inspect_ai.util import SandboxEnvironmentSpec
from inspect_flow import (
    FlowDependencies,
    FlowFactory,
    FlowModel,
    FlowOptions,
    FlowSolver,
    FlowSpec,
    FlowTask,
)
from inspect_flow._display.run_action import RunAction
from inspect_flow._launcher.auto_dependencies import (
    _MODEL_PROVIDERS,
    collect_auto_dependencies,
)
from inspect_flow._launcher.freeze import (
    _deduplicate_freeze_requirements,
    write_flow_requirements,
)
from inspect_flow._launcher.pip_string import (
    _get_pip_string_with_version,
    get_pip_string,
)
from inspect_flow._launcher.venv import _create_venv, venv_launch
from local_eval.noop import noop
from packaging.tags import sys_tags
from rich.console import Console

_test_action = RunAction("test")


@pytest.fixture(autouse=True)
def no_uv_python(monkeypatch: pytest.MonkeyPatch) -> None:
    # CI's setup-uv sets UV_PYTHON, which outranks VIRTUAL_ENV in `uv pip`.
    monkeypatch.delenv("UV_PYTHON", raising=False)


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
            assert args[5:9] == [
                "--python",
                f"{temp_dir}/.venv/bin/python",
                "--project",
                Path.cwd().as_posix(),
            ]
            # A pinned inspect-ai is also a constraint.
            assert set(args[9::2]) <= {"--constraints", "--build-constraints"}
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


def test_671_vcs_url_dependency() -> None:
    base_dir = Path(__file__).parent.resolve().as_posix()
    vcs_url = "git+https://github.com/meridianlabs-ai/flow_steps_demo.git@main"
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
                    dependency_file="no_file",
                    additional_dependencies=[vcs_url],
                ),
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
            vcs_url,
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


def test_715_explicit_dependency_overrides_auto_pin() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )
            spec = FlowSpec(
                dependencies=FlowDependencies(
                    additional_dependencies=["openai>=2.40.0"],
                ),
                tasks=[
                    FlowTask(
                        name="inspect_evals/task_name",
                        model="openai/gpt-4o-mini",
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
            # The explicit "openai>=2.40.0" pin must win; the auto-detected
            # "openai==<host version>" must be excluded to avoid a conflict.
            assert args[:6] == [
                "uv",
                "pip",
                "install",
                "openai>=2.40.0",
                "inspect_evals",
                f"-e {flow_path}",
            ]
            assert not any(arg.startswith("openai==") for arg in args)


def test_715_collect_auto_dependencies_exclude_packages() -> None:
    spec = FlowSpec(
        tasks=[
            FlowTask(name="inspect_evals/task_name", model="openai/gpt-4o-mini"),
        ]
    )

    dependencies = collect_auto_dependencies(spec)
    assert any(dep.startswith("openai") for dep in dependencies)

    # Canonicalization should match regardless of name normalization.
    excluded = collect_auto_dependencies(spec, exclude_packages=["OpenAI"])
    assert not any(dep.startswith("openai") for dep in excluded)
    assert "inspect_evals" in excluded


def test_cloudflare_provider_adds_openai_dependency() -> None:
    # inspect-ai 0.3.248 renamed the "cf" provider to "cloudflare"; both
    # prefixes use an OpenAI-compatible API that requires the openai package.
    for model in ["cf/meta/llama-3.1-8b-instruct", "cloudflare/moonshotai/kimi-k3"]:
        spec = FlowSpec(tasks=[FlowTask(name="inspect_evals/task_name", model=model)])
        dependencies = collect_auto_dependencies(spec)
        assert dependencies == [
            "inspect_evals",
            _get_pip_string_with_version("openai"),
        ]


def test_moonshot_provider_adds_openai_dependency() -> None:
    # inspect-ai 0.3.249 added the "moonshot" provider, which uses an
    # OpenAI-compatible API that requires the openai package.
    spec = FlowSpec(
        tasks=[FlowTask(name="inspect_evals/task_name", model="moonshot/kimi-k3")]
    )
    dependencies = collect_auto_dependencies(spec)
    assert dependencies == [
        "inspect_evals",
        _get_pip_string_with_version("openai"),
    ]


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("openai-api/xai/grok-4-0709", ["openai"]),
        ("openai-api-completions/xai/grok-4-0709", ["openai"]),
        ("deepseek/deepseek-chat", ["openai"]),
        ("meta/muse-spark-1.3", ["openai"]),
        ("litellm-proxy/gpt-4o", ["openai"]),
        ("sagemaker/my-endpoint", ["openai"]),
        ("vllm-completions/meta-llama/Llama-3.1-8B", ["vllm"]),
        ("nnterp/gpt2", ["nnterp"]),
        ("none/none", []),
    ],
)
def test_819_builtin_provider_dependencies(model: str, expected: list[str]) -> None:
    # Built-in providers with no table entry fell through to "the prefix is the
    # PyPI package", requiring nonexistent or unrelated distributions.
    spec = FlowSpec(tasks=[FlowTask(name="inspect_evals/task_name", model=model)])
    assert collect_auto_dependencies(spec) == [
        "inspect_evals",
        *[_get_pip_string_with_version(dep) for dep in expected],
    ]


def test_819_model_providers_cover_inspect_ai_registry() -> None:
    # Every built-in @modelapi provider must have a table entry so a new
    # provider cannot silently fall through to the "prefix is a PyPI package"
    # guess. Legacy aliases like "cf" may remain in the table.
    entries = registry_find(lambda info: info.type == "modelapi")
    builtin = {
        registry_info(e).name.removeprefix("inspect_ai/")
        for e in entries
        if registry_info(e).name.startswith("inspect_ai/")
    }
    assert builtin
    assert builtin <= _MODEL_PROVIDERS.keys()


@pytest.mark.parametrize("model", ["anthropic/claude-x", "openai/gpt-x"])
def test_885_locked_provider_sdks_initialize(model: str) -> None:
    # Child environments copy the host's provider SDK versions, so the locked
    # SDKs must satisfy the locked inspect-ai's provider minimums.
    get_model(model, api_key="test")


def test_826_builtin_providers_do_not_load_entry_points() -> None:
    # Other tests load entry points, so check launcher imports in a fresh process.
    subprocess.run(
        [sys.executable, "tests/fixtures/builtin_model_dependencies.py"], check=True
    )


@pytest.mark.parametrize(
    ("registered_name", "expected_package"),
    [
        ("cf_compat/cf", "cf_compat"),
        ("inspect_ai/future_provider", "future_provider"),
    ],
)
def test_827_registered_provider_dependencies(
    registered_name: str, expected_package: str
) -> None:
    # Keep synthetic registrations out of the registry used by other tests.
    subprocess.run(
        [
            sys.executable,
            "tests/fixtures/registered_model_dependencies.py",
            registered_name,
            expected_package,
        ],
        check=True,
    )


def test_818_registered_provider_resolves_to_its_package() -> None:
    # A third-party @modelapi provider is registered under its package, so the
    # registry names the dependency rather than the "prefix is a PyPI package"
    # guess, which would require a nonexistent "local_eval_provider" package.
    # Loading the module by path (as a task file would be) registers the same
    # provider again without a package; the qualified entry must still win.
    load_module(Path("tests/local_eval/src/local_eval/my_provider.py"))
    spec = FlowSpec(tasks=[FlowTask(model="local_eval_provider/some-model")])
    assert collect_auto_dependencies(spec) == [get_pip_string("local_eval")]


def test_auto_dependency_list_valued_model_role() -> None:
    # a list-valued role binds several models to one role; every element's
    # provider package must be collected
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="inspect_evals/task_name",
                model_roles={
                    "grader": ["groq/model-a", FlowModel(name="google/gemini-1")]
                },
            )
        ]
    )
    assert collect_auto_dependencies(spec) == [
        _get_pip_string_with_version("google-genai"),
        _get_pip_string_with_version("groq"),
        "inspect_evals",
    ]


def test_779_auto_dependency_inline_scanner_models() -> None:
    # options.scanner runs inside the venv, so its model and role providers
    # must be installed alongside the task providers
    spec = FlowSpec(
        tasks=[FlowTask(name="inspect_evals/task_name", model="openai/gpt-4o")],
        options=FlowOptions(
            scanner=ScannerConfig(
                scanners=["scanner_name"],
                model="google/gemini-2.5-pro",
                model_roles={"grader": "groq/model-a"},
            )
        ),
    )
    assert collect_auto_dependencies(spec) == [
        _get_pip_string_with_version("google-genai"),
        _get_pip_string_with_version("groq"),
        "inspect_evals",
        _get_pip_string_with_version("openai"),
    ]


def test_779_flow_model_string_factory_is_the_model_id() -> None:
    # a string factory is passed to get_model(model=...) and wins over name
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="inspect_evals/task_name",
                model=FlowModel(name="anthropic/claude-x", factory="openai/gpt-4o"),
            )
        ]
    )
    assert collect_auto_dependencies(spec) == [
        "inspect_evals",
        _get_pip_string_with_version("openai"),
    ]


def test_820_string_factory_adds_registry_package() -> None:
    # the runner resolves a string factory before name, so the package it
    # references must be installed, whether given bare or via FlowFactory
    for factory in ["inspect_evals/gsm8k", FlowFactory("inspect_evals/gsm8k")]:
        spec = FlowSpec(
            tasks=[
                FlowTask(
                    name="other_pkg/task_name",
                    factory=factory,
                    model="openai/gpt-4o",
                    solver=FlowSolver(factory="my_solvers/react_plus"),
                )
            ]
        )
        assert collect_auto_dependencies(spec) == [
            "inspect_evals",
            "my_solvers",
            _get_pip_string_with_version("openai"),
        ]


def test_820_registry_callable_factory_adds_its_package() -> None:
    # a registry callable is serialized as its pkg/name and resolved in the
    # child through the registry, so its package must be installed; name is
    # never resolved when a callable factory is given
    for factory in [noop, FlowFactory(noop)]:
        spec = FlowSpec(
            tasks=[
                FlowTask(
                    name="other_pkg/task_name", factory=factory, model="openai/gpt-4o"
                )
            ]
        )
        assert collect_auto_dependencies(spec) == [
            get_pip_string("local_eval"),
            _get_pip_string_with_version("openai"),
        ]


def test_820_unregistered_callable_factory_adds_nothing() -> None:
    # a partial has no registry entry (and no __code__), so there is nothing
    # static to install, and its name is never resolved either
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="other_pkg/task_name", factory=partial(noop), model="openai/gpt-4o"
            )
        ]
    )
    assert collect_auto_dependencies(spec) == [_get_pip_string_with_version("openai")]


def test_779_fallback_models_do_not_add_providers() -> None:
    # fallback_models are provider-native ids; a slash in one is part of the
    # id (e.g. an OpenRouter model), not an inspect provider prefix
    spec = FlowSpec(
        tasks=[
            FlowTask(
                name="inspect_evals/task_name",
                model="openai/gpt-4o",
                config=GenerateConfig(fallback_models=["meta-llama/llama-3"]),
            )
        ]
    )
    assert collect_auto_dependencies(spec) == [
        "inspect_evals",
        _get_pip_string_with_version("openai"),
    ]


def test_779_scanner_file_path_adds_nothing() -> None:
    spec = FlowSpec(
        tasks=[FlowTask(name="inspect_evals/task_name", model="openai/gpt-4o")],
        options=FlowOptions(scanner="scanner.yaml"),
    )
    assert collect_auto_dependencies(spec) == [
        "inspect_evals",
        _get_pip_string_with_version("openai"),
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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
                ".venv",
                "--python",
                "3.11",
                "--project",
                "/",
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


def test_inspect_ai_version_via_additional_dependencies() -> None:
    """When the user pins inspect-ai in additional_dependencies, the venv
    setup must install that exact version rather than the auto-pinned
    currently-installed version."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="mocked output"
            )

            _create_venv(
                spec=FlowSpec(
                    dependencies=FlowDependencies(
                        additional_dependencies=["inspect-ai==0.3.100"],
                    ),
                    tasks=[FlowTask(name="task_name")],
                ),
                base_dir=".",
                temp_dir=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                action=_test_action,
            )

            args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert args == [
                "uv",
                "pip",
                "install",
                "inspect-ai==0.3.100",
                f"-e {flow_path}",
                "--python",
                f"{temp_dir}/.venv/bin/python",
                "--project",
                Path.cwd().as_posix(),
            ]


def test_inspect_ai_version_via_dependency_file_requirements() -> None:
    """When the user pins inspect-ai in a requirements.txt dependency_file,
    the venv setup must install that file and must not also append the
    auto-pinned inspect-ai (which would override the user's version)."""
    with tempfile.TemporaryDirectory() as base_dir:
        req_file = Path(base_dir) / "requirements.txt"
        req_file.write_text("inspect-ai==0.3.100\n")

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="mocked output"
                )

                _create_venv(
                    spec=FlowSpec(
                        dependencies=FlowDependencies(
                            dependency_file=req_file.as_posix(),
                        ),
                        tasks=[FlowTask(name="task_name")],
                    ),
                    base_dir=base_dir,
                    temp_dir=temp_dir,
                    env=os.environ.copy(),
                    dry_run=False,
                    action=_test_action,
                )

            assert mock_run.call_count == 3

            install_req_args = mock_run.mock_calls[1].args[0]
            assert install_req_args[:5] == [
                "uv",
                "pip",
                "install",
                "-r",
                req_file.as_posix(),
            ]

            last_args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert last_args[:5] == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
                "--python",
            ]


def test_inspect_ai_version_via_dependency_file_pyproject() -> None:
    """When the user pins inspect-ai in a pyproject.toml dependency_file,
    the venv setup must use that file and must not also append the
    auto-pinned inspect-ai (which would override the user's version)."""
    with tempfile.TemporaryDirectory() as base_dir:
        pyproject_file = Path(base_dir) / "pyproject.toml"
        pyproject_file.write_text(
            "[project]\n"
            'name = "test_project"\n'
            'version = "0.1.0"\n'
            'requires-python = ">=3.10"\n'
            'dependencies = ["inspect-ai==0.3.100"]\n'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="mocked output"
                )

                _create_venv(
                    spec=FlowSpec(
                        dependencies=FlowDependencies(
                            dependency_file=pyproject_file.as_posix(),
                        ),
                        python_version="3.11",
                        tasks=[FlowTask(name="task_name")],
                    ),
                    base_dir=base_dir,
                    temp_dir=temp_dir,
                    env=os.environ.copy(),
                    dry_run=False,
                    action=_test_action,
                )

            # The workspace lock lookup, `uv sync` and `uv pip install`.
            assert mock_run.call_count == 3

            last_args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert last_args[:5] == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
                "--python",
            ]


@pytest.mark.slow
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


@pytest.mark.slow
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


def test_712_concurrent_flow_requirements_no_race() -> None:
    # Two flow runs sharing a working directory must not collide on the
    # intermediate requirements input file written by write_flow_requirements.
    with tempfile.TemporaryDirectory() as temp_dir:
        cwd = Path(temp_dir) / "cwd"
        cwd.mkdir()
        thread_freeze = {
            "run-a": "package-a==1.0.0\n",
            "run-b": "package-b==2.0.0\n",
        }
        log_dirs = {
            "run-a": Path(temp_dir) / "logs-a",
            "run-b": Path(temp_dir) / "logs-b",
        }
        # Block all compile calls until both threads have written their input
        # file, maximizing the chance a shared filename would be clobbered.
        compile_barrier = threading.Barrier(2)

        def fake_run(
            args: list[str], *pos: object, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if args[:3] == ["uv", "pip", "freeze"]:
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=thread_freeze[threading.current_thread().name],
                )
            # uv pip compile: echo back the contents of the input file so a
            # clobbered file would surface as wrong flow-requirements.txt.
            compile_barrier.wait()
            requirements_in = Path(args[-1])
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=requirements_in.read_text()
            )

        errors: dict[str, BaseException] = {}

        def run(name: str) -> None:
            try:
                write_flow_requirements(
                    spec=FlowSpec(
                        log_dir=log_dirs[name].as_posix(),
                        tasks=[FlowTask(name="task_name")],
                    ),
                    cwd=str(cwd),
                    env=os.environ.copy(),
                    dry_run=False,
                    python=sys.executable,
                )
            except BaseException as e:  # noqa: BLE001
                errors[name] = e

        with patch("subprocess.run", side_effect=fake_run):
            threads = [
                threading.Thread(target=run, name=n, args=(n,)) for n in thread_freeze
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert not errors, errors
        for name, expected in thread_freeze.items():
            requirements_txt = log_dirs[name] / "flow-requirements.txt"
            assert requirements_txt.read_text() == expected
        # The temporary input files must be cleaned up.
        assert list(cwd.glob("*.in")) == []


def test_freeze_forwards_explicit_interpreter_to_uv() -> None:
    # write_flow_requirements must forward the interpreter it is given to both
    # the freeze and the compile commands (a caller could pass it to one and
    # forget the other). Behavior against a real interpreter is covered by
    # test_freeze_targets_explicit_interpreter_not_virtual_env below.
    with tempfile.TemporaryDirectory() as temp_dir:
        log_dir = Path(temp_dir) / "logs"
        captured: list[list[str]] = []

        def fake_run(
            args: list[str], *pos: object, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            captured.append(args)
            if args[:3] == ["uv", "pip", "freeze"]:
                return subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="package-a==1.0.0\n"
                )
            # uv pip compile: echo back the contents of the input file.
            requirements_in = Path(args[-1])
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=requirements_in.read_text()
            )

        with patch("subprocess.run", side_effect=fake_run):
            write_flow_requirements(
                spec=FlowSpec(
                    log_dir=log_dir.as_posix(),
                    tasks=[FlowTask(name="task_name")],
                ),
                cwd=temp_dir,
                env=os.environ.copy(),
                dry_run=False,
                python="/custom/interpreter/python",
            )

        freeze_cmd = next(c for c in captured if c[:3] == ["uv", "pip", "freeze"])
        assert (
            freeze_cmd[freeze_cmd.index("--python") + 1] == "/custom/interpreter/python"
        )

        compile_cmd = next(c for c in captured if c[:3] == ["uv", "pip", "compile"])
        assert (
            compile_cmd[compile_cmd.index("--python") + 1]
            == "/custom/interpreter/python"
        )


@pytest.mark.slow
def test_freeze_targets_explicit_interpreter_not_virtual_env() -> None:
    # The real freeze must resolve against the explicitly-passed interpreter,
    # not the VIRTUAL_ENV uv would otherwise discover. Point VIRTUAL_ENV (and
    # cwd) at a fresh, empty venv and freeze the running interpreter: the
    # recorded requirements must reflect the running interpreter, not the empty
    # venv (which would freeze to nothing). Only the network-bound compile step
    # is stubbed; the freeze runs for real so it actually exercises `--python`.
    with tempfile.TemporaryDirectory() as temp_dir:
        decoy_venv = Path(temp_dir) / "decoy"
        subprocess.run(
            ["uv", "venv", "--python", sys.executable, str(decoy_venv)],
            check=True,
            capture_output=True,
            text=True,
        )
        cwd = Path(temp_dir) / "cwd"
        cwd.mkdir()
        log_dir = Path(temp_dir) / "logs"

        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(decoy_venv)

        real_run = subprocess.run

        def fake_run(
            args: list[str], *pos: Any, **kwargs: Any
        ) -> subprocess.CompletedProcess[str]:
            # Stub only compile (its --generate-hashes would hit the package
            # index); let the real freeze run against the given interpreter.
            if args[:3] == ["uv", "pip", "compile"]:
                requirements_in = Path(args[-1])
                return subprocess.CompletedProcess(
                    args=args, returncode=0, stdout=requirements_in.read_text()
                )
            return real_run(args, *pos, **kwargs)

        with patch("subprocess.run", side_effect=fake_run):
            write_flow_requirements(
                spec=FlowSpec(
                    log_dir=log_dir.as_posix(),
                    tasks=[FlowTask(name="task_name")],
                ),
                cwd=str(cwd),
                env=env,
                dry_run=False,
                python=sys.executable,
            )

        requirements = (log_dir / "flow-requirements.txt").read_text()
        # pydantic is installed in the running interpreter but not the empty
        # decoy venv, so its presence proves the freeze used --python, not
        # VIRTUAL_ENV. Dropping --python would freeze the empty venv instead.
        assert "pydantic==" in requirements


SEVEN_DAYS = timedelta(days=7)
SIX_HOURS = timedelta(hours=6)
# A package copied from the host: no cooldown.
HOST_PIN = False
DEFAULTS = {
    "*": SEVEN_DAYS,
    "anthropic": SIX_HOURS,
    "inspect-ai": SIX_HOURS,
    "inspect-scout": SIX_HOURS,
    "openai": SIX_HOURS,
}
USER_CUTOFF = "2026-01-02T03:04:05Z"
USER_OPENAI_CUTOFF = "2026-01-03T03:04:05Z"
USER_SETTINGS = (
    f'exclude-newer = "{USER_CUTOFF}"\n'
    f'[exclude-newer-package]\nopenai = "{USER_OPENAI_CUTOFF}"\n'
)
PROJECT = '[project]\nname = "p"\nversion = "0.1"\nrequires-python = ">=3.10"\n'

UvCommand = tuple[list[str], dict[str, str], str]


@pytest.fixture
def uv_env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("UV_")}
    env.pop("XDG_CONFIG_HOME", None)
    env["HOME"] = str(tmp_path / "home")
    env["XDG_CONFIG_DIRS"] = str(tmp_path / "system_config")
    return env


def _uv_commands(
    spec: FlowSpec, base_dir: Path, env: dict[str, str]
) -> list[UvCommand]:
    # A sibling, as in production: uv must not find base_dir's settings by
    # walking up from the temp dir.
    temp_dir = base_dir.with_name(base_dir.name + "-venv")
    temp_dir.mkdir(exist_ok=True)

    real_run = subprocess.run

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        # Queries that change nothing run for real.
        if args[:2] == ["uv", "workspace"] or args[0] != "uv":
            return real_run(args, **kwargs)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="mocked output"
        )

    with patch("subprocess.run", side_effect=run) as mock_run:
        _create_venv(
            spec=spec,
            base_dir=base_dir.as_posix(),
            temp_dir=temp_dir.as_posix(),
            env=env,
            dry_run=False,
            action=_test_action,
        )
    return [
        (c.args[0], c.kwargs["env"], c.kwargs["cwd"]) for c in mock_run.call_args_list
    ]


def _command(commands: list[UvCommand], *prefix: str) -> UvCommand:
    (command,) = [c for c in commands if c[0][: len(prefix)] == list(prefix)]
    return command


def _flow_settings(command: UvCommand) -> dict[str, Any]:
    config_dir = command[1]["XDG_CONFIG_DIRS"].split(os.pathsep)[0]
    config_file = Path(config_dir) / "uv" / "uv.toml"
    return tomllib.loads(config_file.read_text())


def _flow_cooldowns(command: UvCommand) -> dict[str, timedelta | bool]:
    # The age of each cutoff in flow's settings, to the minute; "*" for all
    # packages, and False for none.
    settings = _flow_settings(command)
    cutoffs = {"*": settings["exclude-newer"]} if "exclude-newer" in settings else {}
    cutoffs.update(settings.get("exclude-newer-package", {}))
    now = datetime.now(UTC)
    return {
        package: cutoff
        if cutoff is False
        else timedelta(
            minutes=round((now - datetime.fromisoformat(cutoff)).total_seconds() / 60)
        )
        for package, cutoff in cutoffs.items()
    }


def _project_option(command: UvCommand) -> str | None:
    args = command[0]
    return args[args.index("--project") + 1] if "--project" in args else None


def test_cooldown_no_file(tmp_path: Path, uv_env: dict[str, str]) -> None:
    spec = FlowSpec(
        log_dir=(tmp_path / "logs").as_posix(),
        dependencies=FlowDependencies(dependency_file="no_file"),
        tasks=[FlowTask(name="task_name", model="anthropic/claude-x")],
    )
    commands = _uv_commands(spec, tmp_path, uv_env)

    venv = _command(commands, "uv", "venv")
    # Without a dependency file, uv reads the settings where the spec is.
    assert _project_option(venv) == str(tmp_path)
    # `uv venv` installs seed packages when UV_VENV_SEED is set.
    assert _flow_cooldowns(venv) == DEFAULTS
    seeded = (venv[0], {**venv[1], "UV_VENV_SEED": "1"}, venv[2])
    assert _uv_cutoffs(_uv_settings_output(seeded))["*"] == {
        _flow_settings(venv)["exclude-newer"]
    }
    install = _command(commands, "uv", "pip", "install")
    assert _project_option(install) == str(tmp_path)
    # anthropic and inspect-ai are pinned to the versions installed here.
    inspect_ai = HOST_PIN if "==" in get_pip_string("inspect-ai") else SIX_HOURS
    assert _flow_cooldowns(install) == {
        **DEFAULTS,
        "anthropic": HOST_PIN,
        "inspect-ai": inspect_ai,
    }
    # Recording the venv's packages uses only the user's own uv settings.
    compiled = _command(commands, "uv", "pip", "compile")
    assert compiled[1] == uv_env
    assert "--project" not in compiled[0]


def _wheel(
    directory: Path,
    name: str,
    version: str,
    tag: str = "py3-none-any",
    metadata: str = "",
) -> None:
    # A wheel with metadata only, for a local package index.
    dist_info = f"{name.replace('-', '_')}-{version}.dist-info"
    files = {
        f"{dist_info}/METADATA": f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n{metadata}",
        f"{dist_info}/WHEEL": f"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: {tag}\n",
    }
    record = "".join(f"{n},,\n" for n in [*files, f"{dist_info}/RECORD"])
    directory.mkdir(parents=True, exist_ok=True)
    wheel = directory / f"{name.replace('-', '_')}-{version}-{tag}.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        for n, text in files.items():
            z.writestr(n, text)
        z.writestr(f"{dist_info}/RECORD", record)


@contextmanager
def _simple_index(wheels: Path, upload_times: dict[str, str | None]) -> Iterator[str]:
    # A PEP 691 index of the wheels, with each one's upload time, or none.
    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            self.do_GET(body=False)

        def do_GET(self, body: bool = True) -> None:
            base = f"http://{self.headers['Host']}"
            kind, name = unquote(self.path).strip("/").split("/")
            if kind == "files":
                content = (wheels / name).read_bytes()
                content_type = "application/octet-stream"
            else:
                files = [
                    {
                        "filename": w.name,
                        "url": f"{base}/files/{w.name}",
                        "hashes": {
                            "sha256": hashlib.sha256(w.read_bytes()).hexdigest()
                        },
                        **(
                            {"upload-time": upload_times[w.name]}
                            if upload_times[w.name]
                            else {}
                        ),
                    }
                    for w in wheels.glob(f"{name.replace('-', '_')}-*.whl")
                ]
                index = {"meta": {"api-version": "1.1"}, "name": name, "files": files}
                content = json.dumps(index).encode()
                content_type = "application/vnd.pypi.simple.v1+json"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            if body:
                self.wfile.write(content)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/simple"
    finally:
        server.shutdown()
        server.server_close()


def _install_copied_dep(
    tmp_path: Path,
    uv_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    host_version: str,
    upload_times: dict[str, str | None],
    uv_toml: str = "",
) -> subprocess.CompletedProcess[str]:
    # Runs flow's final install of copied-dep, copied from the host at
    # `host_version`, from an index of the given versions and upload times.
    wheels = tmp_path / "wheels"
    for version in upload_times:
        _wheel(wheels, "copied-dep", version)
    host = tmp_path / "host" / f"copied_dep-{host_version}.dist-info"
    host.mkdir(parents=True)
    (host / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: copied-dep\nVersion: {host_version}\n"
    )
    monkeypatch.syspath_prepend(str(host.parent))
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
    base_dir = tmp_path / "spec"
    base_dir.mkdir()
    (base_dir / "uv.toml").write_text(uv_toml)
    venv = base_dir.with_name("spec-venv") / ".venv"
    subprocess.run(
        ["uv", "venv", str(venv), "--python", sys.executable, "--offline"],
        env=uv_env,
        check=True,
        capture_output=True,
    )
    spec = FlowSpec(
        dependencies=FlowDependencies(dependency_file="no_file"),
        tasks=[FlowTask(name="copied_dep/task")],
    )
    files = {
        f"copied_dep-{version}-py3-none-any.whl": time
        for version, time in upload_times.items()
    }

    with _simple_index(wheels, files) as index_url:
        uv_env.update(UV_INDEX_URL=index_url, UV_NO_CACHE="1")
        args, env, cwd = _command(
            _uv_commands(spec, base_dir, uv_env), "uv", "pip", "install"
        )
        pin = f"copied_dep=={host_version}"
        assert pin in args
        return subprocess.run(
            ["uv", "pip", "install", pin] + args[args.index("--python") :],
            env=env,
            cwd=cwd,
            capture_output=True,
            text=True,
        )


def _an_hour_ago() -> str:
    return (datetime.now(UTC) - timedelta(hours=1)).isoformat()


@pytest.mark.parametrize("override", [False, True])
def test_host_pin_exempt_only_at_its_version(
    tmp_path: Path,
    uv_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    override: bool,
) -> None:
    # The host has copied-dep 2.0, which the index lists with no upload date, as
    # a private index might. 3.0 was uploaded an hour ago. The exemption must
    # not let an override install the new release.
    result = _install_copied_dep(
        tmp_path,
        uv_env,
        monkeypatch,
        "2.0",
        {"2.0": None, "3.0": _an_hour_ago()},
        'override-dependencies = ["copied-dep==3.0"]\n' if override else "",
    )

    if override:
        assert result.returncode != 0
        assert "copied-dep==3.0" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert "+ copied-dep==2.0" in result.stderr


@pytest.mark.parametrize("host_version", ["2.0", "2.0+cu128"])
def test_host_pin_keeps_local_label(
    tmp_path: Path,
    uv_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    host_version: str,
) -> None:
    # `==2.0` also matches 2.0+cu129, a local build uploaded an hour ago, which
    # the exemption would let through.
    result = _install_copied_dep(
        tmp_path,
        uv_env,
        monkeypatch,
        host_version,
        {"2.0": None, "2.0+cu128": None, "2.0+cu129": _an_hour_ago()},
    )

    assert result.returncode == 0, result.stderr
    installed = [line.strip() for line in result.stderr.splitlines()]
    assert f"+ copied-dep=={host_version}" in installed


def test_install_holds_build_requirements_to_host_versions(
    tmp_path: Path, uv_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # overlap-dep is copied from the host at 1.0 and is also a build requirement
    # of another dependency, as torch is for a CUDA extension. A local index
    # offers 1.0 and 2.0 of each build requirement.
    wheels = tmp_path / "wheels"
    for name in ("overlap-dep", "overlap-other"):
        for version in ("1.0", "2.0"):
            _wheel(wheels, name, version)
    host = tmp_path / "host" / "overlap_dep-1.0.dist-info"
    host.mkdir(parents=True)
    (host / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: overlap-dep\nVersion: 1.0\n"
    )
    monkeypatch.syspath_prepend(str(host.parent))
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
    package = tmp_path / "overlap-package"
    shutil.copytree(Path(__file__).parent / "fixtures" / "build_overlap", package)
    user_constraints = tmp_path / "user-build-constraints.txt"
    user_constraints.write_text("overlap-other<2\n")
    uv_env.update(
        UV_NO_CACHE="1",
        UV_NO_INDEX="1",
        UV_FIND_LINKS=str(wheels),
        UV_BUILD_CONSTRAINT=str(user_constraints),
    )
    # A space in flow's temp dir must not split the build-constraints file name.
    base_dir = tmp_path / "spec dir"
    base_dir.mkdir()
    spec = FlowSpec(
        dependencies=FlowDependencies(
            dependency_file="no_file", additional_dependencies=[str(package)]
        ),
        tasks=[FlowTask(name="overlap_dep/task")],
    )
    args, env, cwd = _command(
        _uv_commands(spec, base_dir, uv_env), "uv", "pip", "install"
    )
    assert "overlap_dep==1.0" in args

    # Install the overlapping packages with the captured options, offline.
    python = Path(args[args.index("--python") + 1])
    subprocess.run(
        ["uv", "venv", str(python.parents[1]), "--python", sys.executable],
        env=uv_env,
        check=True,
        capture_output=True,
    )
    packages = [a for a in args[3 : args.index("--python")] if "overlap" in a]
    subprocess.run(
        ["uv", "pip", "install", *packages, *args[args.index("--python") :]],
        env=env,
        cwd=cwd,
        check=True,
        capture_output=True,
    )

    # The build could take overlap-dep 2.0, but is held to the host's 1.0; the
    # user's constraint still holds overlap-other.
    seen = (package / "build-saw.txt").read_text()
    assert seen == repr({"overlap-dep": "1.0", "overlap-other": "1.0"})
    frozen = subprocess.run(
        ["uv", "pip", "freeze", "--python", str(python)],
        env=uv_env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "overlap-dep==1.0" in frozen.splitlines()


def test_cooldown_requirements_txt(tmp_path: Path, uv_env: dict[str, str]) -> None:
    (tmp_path / "requirements.txt").write_text("inspect-ai\n")
    spec = FlowSpec(
        dependencies=FlowDependencies(dependency_file="requirements.txt"),
        tasks=[FlowTask(name="task_name")],
    )
    commands = _uv_commands(spec, tmp_path, uv_env)

    assert _project_option(_command(commands, "uv", "venv")) == str(tmp_path)
    requirements = _command(commands, "uv", "pip", "install", "-r")
    assert _project_option(requirements) == str(tmp_path)
    assert _flow_cooldowns(requirements) == DEFAULTS
    (install,) = [c for c in commands[1:] if c[0][3] != "-r"]
    assert _project_option(install) == str(tmp_path)
    assert _flow_cooldowns(install) == DEFAULTS


def test_install_stays_in_venv(tmp_path: Path, uv_env: dict[str, str]) -> None:
    # The project's uv settings must not choose another environment.
    (tmp_path / "requirements.txt").write_text("inspect-ai\n")
    (tmp_path / "uv.toml").write_text(f"[pip]\npython = {json.dumps(sys.executable)}\n")
    venv = tmp_path.with_name(tmp_path.name + "-venv") / ".venv"
    subprocess.run(
        ["uv", "venv", str(venv), "--python", sys.executable, "--offline"],
        env=uv_env,
        check=True,
        capture_output=True,
    )
    spec = FlowSpec(
        dependencies=FlowDependencies(dependency_file="requirements.txt"),
        tasks=[FlowTask(name="task_name")],
    )
    installs = [
        c
        for c in _uv_commands(spec, tmp_path, uv_env)
        if c[0][:3] == ["uv", "pip", "install"]
    ]

    assert len(installs) == 2
    for args, env, _ in installs:
        # A dry run of an unknown package names the environment uv would install
        # into, offline. uv omits the name for a `.venv` in the working directory.
        result = subprocess.run(
            ["uv", "pip", "install", "no-such-package"]
            + args[args.index("--python") :]
            + ["--offline", "--dry-run"],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        target = re.search(r"environment at: (.+)", result.stderr)
        assert target, result.stderr
        assert Path(target[1]).resolve() == venv.resolve()


def test_install_uses_venv_python_version(
    tmp_path: Path, uv_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A project `python-version` must not choose wheels for another interpreter.
    # The only foreign wheel is for Python 3.9 on this platform. `patchy` needs
    # this interpreter's patch version, and so does its dependency `leaf`.
    wheels = tmp_path / "wheels"
    _wheel(wheels, "foreign", "1.0", f"cp39-cp39-{next(sys_tags()).platform}")
    full = ".".join(map(str, sys.version_info[:3]))
    _wheel(
        wheels,
        "patchy",
        "1.0",
        metadata=f'Requires-Python: >={full}\nRequires-Dist: leaf; python_full_version >= "{full}"\n',
    )
    _wheel(wheels, "leaf", "1.0")
    uv_env.update(UV_NO_INDEX="1", UV_FIND_LINKS=str(wheels), UV_NO_CACHE="1")
    (tmp_path / "requirements.txt").write_text("inspect-ai\n")
    (tmp_path / "uv.toml").write_text('[pip]\npython-version = "3.9"\n')
    venv = tmp_path.with_name(tmp_path.name + "-venv") / ".venv"
    subprocess.run(
        ["uv", "venv", str(venv), "--python", sys.executable, "--offline"],
        env=uv_env,
        check=True,
        capture_output=True,
    )
    # uv sometimes records only the minor version.
    config = venv / "pyvenv.cfg"
    minor = ".".join(map(str, sys.version_info[:2]))
    config.write_text(
        re.sub(
            r"(?m)^version_info = .*$", f"version_info = {minor}", config.read_text()
        )
    )
    spec = FlowSpec(
        dependencies=FlowDependencies(dependency_file="requirements.txt"),
        tasks=[FlowTask(name="task_name")],
    )
    # The version query runs with flow's environment, which has no PYTHONHOME,
    # not with this process's broken one.
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "no-python-home"))
    installs = [
        c
        for c in _uv_commands(spec, tmp_path, uv_env)
        if c[0][:3] == ["uv", "pip", "install"]
    ]

    assert len(installs) == 2
    for args, env, cwd in installs:
        options = args[args.index("--python") :]
        version = options.index("--python-version")
        without_version = options[:version] + options[version + 2 :]
        for uv_options, selected in ((options, False), (without_version, True)):
            result = subprocess.run(
                ["uv", "pip", "install", "foreign==1.0"]
                + uv_options
                + ["--offline", "--dry-run"],
                env=env,
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            assert (result.returncode == 0) == selected, result.stderr
        result = subprocess.run(
            ["uv", "pip", "install", "patchy==1.0"]
            + options
            + ["--offline", "--dry-run"],
            env=env,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "+ leaf==1.0" in result.stderr


@pytest.mark.parametrize("locked", [False, True])
def test_cooldown_sync(tmp_path: Path, uv_env: dict[str, str], locked: bool) -> None:
    (tmp_path / "pyproject.toml").write_text(PROJECT)
    if locked:
        (tmp_path / "uv.lock").write_text("")
    spec = FlowSpec(python_version="3.11", tasks=[FlowTask(name="task_name")])
    sync = _command(_uv_commands(spec, tmp_path, uv_env), "uv", "sync")

    assert _project_option(sync) == str(tmp_path)
    assert ("--frozen" in sync[0]) == locked
    # A lock does not cover build requirements, so a locked sync gets the default too.
    assert _flow_cooldowns(sync) == DEFAULTS


def _locked_workspace(tmp_path: Path, uv_env: dict[str, str]) -> Path:
    # A workspace and its lock, with no dependencies; returns the member.
    root = tmp_path / "workspace"
    member = root / "member"
    member.mkdir(parents=True)
    workspace = '[tool.uv.workspace]\nmembers = ["member"]\n'
    (root / "pyproject.toml").write_text(PROJECT.replace('"p"', '"root"') + workspace)
    (member / "pyproject.toml").write_text(PROJECT)
    uv_env.update(
        UV_CACHE_DIR=str(tmp_path / "cache"), VIRTUAL_ENV=str(tmp_path / "venv")
    )
    subprocess.run(
        ["uv", "lock", "--project", str(member), "--offline"],
        env=uv_env,
        check=True,
        capture_output=True,
    )
    return member


def test_workspace_member_lock_is_frozen(
    tmp_path: Path, uv_env: dict[str, str]
) -> None:
    # A workspace member uses the lock at the workspace root.
    member = _locked_workspace(tmp_path, uv_env)
    root = member.parent
    lock = (root / "uv.lock").read_text()
    spec = FlowSpec(python_version=sys.executable, tasks=[FlowTask(name="task_name")])
    args, env, cwd = _command(_uv_commands(spec, member, uv_env), "uv", "sync")

    assert "--frozen" in args
    subprocess.run(
        args + ["--offline"], env=env, cwd=cwd, check=True, capture_output=True
    )
    assert (root / "uv.lock").read_text() == lock


@pytest.mark.parametrize("mode", ["--locked", "--frozen"])
def test_explicit_lock_mode_is_kept(
    tmp_path: Path, uv_env: dict[str, str], mode: str
) -> None:
    member = _locked_workspace(tmp_path, uv_env)
    spec = FlowSpec(
        python_version=sys.executable,
        dependencies=FlowDependencies(uv_sync_args=[mode]),
        tasks=[FlowTask(name="task_name")],
    )
    args, env, cwd = _command(_uv_commands(spec, member, uv_env), "uv", "sync")

    assert [a for a in args if a in ("--locked", "--frozen")] == [mode]
    # uv accepts the arguments.
    subprocess.run(
        args + ["--offline", "--show-settings"],
        env=env,
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_env_lock_mode_is_kept(tmp_path: Path, uv_env: dict[str, str]) -> None:
    # UV_LOCKED rejects a stale lock; flow's --frozen would accept it.
    member = _locked_workspace(tmp_path, uv_env)
    pyproject = member / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace(">=3.10", ">=3.11"))
    uv_env["UV_LOCKED"] = "1"
    spec = FlowSpec(python_version=sys.executable, tasks=[FlowTask(name="task_name")])
    args, env, cwd = _command(_uv_commands(spec, member, uv_env), "uv", "sync")

    result = subprocess.run(
        args + ["--offline"], env=env, cwd=cwd, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "needs to be updated" in result.stderr


# Valid to uv, but not to Python's TOML parser: Flow must not read the file.
UV_ONLY_SYNTAX = 'exclude-newer-package = { openai = "1 day", }\n'


@pytest.mark.parametrize("discovery", [True, False])
def test_system_config_turns_off_default(
    tmp_path: Path,
    uv_env: dict[str, str],
    recording_console: Console,
    discovery: bool,
) -> None:
    system = tmp_path / "system_config" / "uv" / "uv.toml"
    system.parent.mkdir(parents=True)
    system.write_text(UV_ONLY_SYNTAX)
    if not discovery:
        uv_env["UV_NO_SYSTEM_CONFIG"] = "1"
    spec = FlowSpec(
        dependencies=FlowDependencies(dependency_file="no_file"),
        tasks=[FlowTask(name="task_name")],
    )
    commands = _uv_commands(spec, tmp_path, uv_env)

    warned = str(system) in recording_console.export_text()
    if discovery:
        assert warned
        # Flow leaves the system file to work alone.
        assert all(env == uv_env for _, env, _ in commands)
        output = _uv_settings_output(_command(commands, "uv", "pip", "install"))
        assert _uv_cutoffs(output) == {"*": set(), "openai": set(), "anthropic": set()}
    else:
        # uv ignores the system file, so Flow neither reads it nor warns.
        assert not warned
        assert _flow_cooldowns(_command(commands, "uv", "venv")) == DEFAULTS


@pytest.mark.parametrize("option", ["env", "sync_args"])
def test_explicit_config_turns_off_default(
    tmp_path: Path,
    uv_env: dict[str, str],
    recording_console: Console,
    option: str,
) -> None:
    (tmp_path / "pyproject.toml").write_text(PROJECT)
    custom = tmp_path / "custom.toml"
    custom.write_text(INDEX_ONLY + UV_ONLY_SYNTAX)
    if option == "env":
        uv_env["UV_CONFIG_FILE"] = str(custom)
    spec = FlowSpec(
        python_version="3.11",
        dependencies=FlowDependencies(
            uv_sync_args=f"--config-file={custom}" if option == "sync_args" else None
        ),
        tasks=[FlowTask(name="task_name")],
    )
    commands = _uv_commands(spec, tmp_path, uv_env)

    assert str(custom) in recording_console.export_text()
    sync = _command(commands, "uv", "sync")
    # uv gets the file as the user named it, and no defaults.
    assert sync[1] == uv_env
    output = _uv_settings_output(sync)
    assert "https://example.invalid/simple" in output
    assert _uv_cutoffs(output) == {"*": set(), "openai": set(), "anthropic": set()}
    install = _command(commands, "uv", "pip", "install")
    if option == "env":
        assert install[1] == uv_env
    else:
        # `--config-file` in uv_sync_args reaches only `uv sync`.
        assert _flow_cooldowns(install)["*"] == SEVEN_DAYS


def _uv_settings_output(command: UvCommand) -> str:
    args, env, cwd = command
    return subprocess.run(
        [*args, "--offline", "--show-settings"],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _uv_cutoffs(output: str) -> dict[str, set[str]]:
    # The cutoffs uv itself settles on, from its --show-settings output.
    timestamp = r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)"
    return {
        "*": set(re.findall(r"\bglobal:[^\"]*?" + timestamp, output)),
        **{
            p: set(re.findall(f'"{p}"[^"]*?' + timestamp, output))
            for p in ("anthropic", "openai")
        },
    }


PROJECT_SETTINGS = (
    PROJECT
    + f'[tool.uv]\nexclude-newer = "{USER_CUTOFF}"\n'
    + f'[tool.uv.exclude-newer-package]\nopenai = "{USER_OPENAI_CUTOFF}"\n'
)
NO_FILE: dict[str, Any] = {"dependency_file": "no_file"}
INDEX_ONLY = 'index-url = "https://example.invalid/simple"\n'


def test_relative_uv_project(
    tmp_path: Path, uv_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # A relative UV_PROJECT is relative to the caller's directory, not the
    # spec's or flow's temp dir.
    caller = tmp_path / "caller"
    (caller / "proj").mkdir(parents=True)
    (caller / "proj" / "pyproject.toml").write_text(PROJECT_SETTINGS)
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()
    monkeypatch.chdir(caller)
    uv_env["UV_PROJECT"] = "proj"
    spec = FlowSpec(
        dependencies=FlowDependencies(dependency_file="no_file"),
        tasks=[FlowTask(name="task_name")],
    )
    commands = _uv_commands(spec, spec_dir, uv_env)

    for command in (
        _command(commands, "uv", "venv"),
        _command(commands, "uv", "pip", "install"),
    ):
        assert command[2] != str(caller)
        assert _uv_cutoffs(_uv_settings_output(command))["*"] == {USER_CUTOFF}


@pytest.mark.parametrize(
    "files,env,dependencies,user_global,user_openai,flow_anthropic",
    [
        pytest.param(
            {"pyproject.toml": PROJECT_SETTINGS}, {}, {}, True, True, True, id="project"
        ),
        pytest.param(
            {
                "pyproject.toml": PROJECT_SETTINGS
                + '[tool.uv.workspace]\nmembers = ["member"]\n',
                "member/pyproject.toml": PROJECT.replace('"p"', '"member"')
                + "[tool.uv]\npackage = true\n",
            },
            {},
            {"dependency_file": "member/pyproject.toml"},
            True,
            True,
            True,
            id="workspace_root",
        ),
        pytest.param(
            {"proj/pyproject.toml": PROJECT_SETTINGS},
            {"UV_PROJECT": "{tmp}/proj"},
            NO_FILE,
            True,
            True,
            True,
            id="uv_project",
        ),
        pytest.param(
            {"home/.config/uv/uv.toml": USER_SETTINGS},
            {},
            NO_FILE,
            True,
            True,
            True,
            id="user_home",
        ),
        pytest.param(
            {}, {"UV_EXCLUDE_NEWER": USER_CUTOFF}, NO_FILE, True, False, True, id="env"
        ),
        pytest.param(
            {"pyproject.toml": PROJECT},
            {},
            {"uv_sync_args": f"--exclude-newer-package openai={USER_OPENAI_CUTOFF}"},
            False,
            True,
            True,
            id="sync_args_package",
        ),
        pytest.param(
            {"uv.toml": INDEX_ONLY + USER_SETTINGS},
            {},
            {},
            True,
            True,
            True,
            id="spec_dir_uv_toml",
        ),
        pytest.param(
            {"uv.toml": INDEX_ONLY + USER_SETTINGS},
            {},
            NO_FILE,
            True,
            True,
            True,
            id="spec_dir_uv_toml_no_file",
        ),
    ],
)
def test_user_settings_override_defaults(
    tmp_path: Path,
    uv_env: dict[str, str],
    files: dict[str, str],
    env: dict[str, str],
    dependencies: dict[str, Any],
    user_global: bool,
    user_openai: bool,
    flow_anthropic: bool,
) -> None:
    def resolve(value: Any) -> Any:
        if isinstance(value, list):
            return [resolve(v) for v in value]
        return (
            value.replace("{tmp}", str(tmp_path)) if isinstance(value, str) else value
        )

    for name, content in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(content)
    uv_env.update({k: resolve(v) for k, v in env.items()})
    spec = FlowSpec(
        python_version="3.11",
        dependencies=FlowDependencies(
            **{k: resolve(v) for k, v in dependencies.items()}
        ),
        tasks=[FlowTask(name="task_name")],
    )
    commands = _uv_commands(spec, tmp_path, uv_env)
    sync = [c for c in commands if c[0][:2] == ["uv", "sync"]]
    command = sync[0] if sync else _command(commands, "uv", "pip", "install")

    flow = _flow_settings(command)
    flow_packages = flow["exclude-newer-package"]
    output = _uv_settings_output(command)
    if any(INDEX_ONLY in content for content in files.values()):
        assert "https://example.invalid/simple" in output
    assert _uv_cutoffs(output) == {
        "*": {USER_CUTOFF if user_global else flow["exclude-newer"]},
        "openai": {USER_OPENAI_CUTOFF if user_openai else flow_packages["openai"]},
        "anthropic": {flow_packages["anthropic"]} if flow_anthropic else set(),
    }
