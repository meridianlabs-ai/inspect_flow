import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Generator
from functools import partial
from importlib import import_module
from importlib.metadata import distribution, packages_distributions
from pathlib import Path
from site import addsitedir
from typing import IO, Any
from unittest.mock import patch

import inspect_ai.model._providers.providers  # noqa: F401  registers @modelapi providers
import pytest
from botocore.client import BaseClient
from inspect_ai import ScannerConfig
from inspect_ai._util.registry import (
    RegistryInfo,
    _registry,
    registry_add,
    registry_find,
    registry_info,
)
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


@pytest.mark.parametrize(
    ("info", "model", "expected"),
    [
        (
            RegistryInfo(type="modelapi", name="my_package/custom-provider"),
            "custom-provider/some-model",
            "custom-provider",
        ),
        (
            RegistryInfo(type="modelapi", name="local-provider"),
            "local-provider/some-model",
            "local-provider",
        ),
        (
            RegistryInfo(type="task", name="other_package/task-provider"),
            "task-provider/some-model",
            "task-provider",
        ),
    ],
)
def test_818_registered_model_provider_dependencies(
    info: RegistryInfo, model: str, expected: str
) -> None:
    def provider() -> None:
        pass

    registry_add(provider, info)
    spec = FlowSpec(tasks=[FlowTask(model=model)])

    assert collect_auto_dependencies(spec) == [expected]


@pytest.fixture
def acme_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
    site_packages = tmp_path / "site-packages"
    dist_info = site_packages / "acme_models-1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: acme-models\nVersion: 1.0\n"
    )
    (dist_info / "top_level.txt").write_text("acme\n")
    shutil.copytree(
        Path(__file__).parent / "model_providers" / "acme", site_packages / "acme"
    )
    (dist_info / "RECORD").write_text(
        "acme/__init__.py,,\nacme/installed.py,,\nacme/editable.py,,\n"
        f"{dist_info.name}/METADATA,,\n"
        f"{dist_info.name}/top_level.txt,,\n"
        f"{dist_info.name}/RECORD,,\n"
    )
    monkeypatch.syspath_prepend(str(site_packages))
    yield dist_info
    for key in list(_registry):
        if key.startswith("modelapi:acme/") or key in (
            "modelapi:editable-acme",
            "modelapi:acme-models",
            "modelapi:lazy-acme",
            "modelapi:acme_core/registered-acme",
            "modelapi:registered-acme",
        ):
            del _registry[key]
    for name in (
        "acme.installed",
        "acme.editable",
        "acme",
        "acme_core",
        "registered_acme",
        "acme_finder",
    ):
        sys.modules.pop(name, None)


@pytest.mark.parametrize("provider_name", ["acme-models", "custom-acme"])
def test_824_model_provider_distribution(
    acme_distribution: Path, provider_name: str
) -> None:
    import_module("acme.installed")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    assert get_model(f"{provider_name}/example").name == "example"
    assert collect_auto_dependencies(spec) == ["acme-models==1.0"]
    assert collect_auto_dependencies(spec, exclude_packages=["ACME_Models"]) == []


@pytest.fixture
def registered_acme_distribution(acme_distribution: Path) -> Path:
    for name in ("acme_core", "registered_acme"):
        dist_info = acme_distribution.parent / f"{name}-1.0.dist-info"
        dist_info.mkdir()
        (dist_info / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {name.replace('_', '-')}\nVersion: 1.0\n"
        )
        (dist_info / "top_level.txt").write_text(f"{name}\n")
        (dist_info / "RECORD").write_text(f"{name}.py,,\n")
        shutil.copyfile(
            Path(__file__).parent / "model_providers" / f"{name}.py",
            acme_distribution.parent / f"{name}.py",
        )
    return acme_distribution.parent / "registered_acme-1.0.dist-info"


@pytest.mark.parametrize("registration", ["installed", "source", "implementation"])
def test_824_model_provider_registration_distribution(
    registered_acme_distribution: Path, registration: str
) -> None:
    expected = ["acme-core==1.0"]
    if registration == "installed":
        expected.append("registered-acme==1.0")
    else:
        shutil.rmtree(registered_acme_distribution)
        if registration == "source":
            expected.append("registered-acme")
        else:
            core = registered_acme_distribution.parent / "acme_core-1.0.dist-info"
            (core / "top_level.txt").write_text("acme_core\nregistered_acme\n")
            (core / "RECORD").write_text("acme_core.py,,\nregistered_acme.py,,\n")
    import_module("registered_acme")
    spec = FlowSpec(tasks=[FlowTask(model="registered-acme/example")])

    assert get_model("registered-acme/example", memoize=False).name == "example"
    assert collect_auto_dependencies(spec) == expected
    assert collect_auto_dependencies(spec, exclude_packages=["REGISTERED_Acme"]) == []


@pytest.mark.parametrize("model_source", ["model", "role", "env", "string_task"])
def test_824_explicit_provider_overrides_host_implementation(
    registered_acme_distribution: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_source: str,
) -> None:
    import_module("registered_acme")
    model = "registered-acme/example"
    task = FlowTask(name="task_name")
    if model_source == "model":
        task.model = model
    elif model_source == "role":
        task.model_roles = {"grader": model}
    else:
        monkeypatch.setenv("INSPECT_EVAL_MODEL", model)
    spec = FlowSpec(
        tasks=[task],
        dependencies=FlowDependencies(
            additional_dependencies=["REGISTERED_Acme==2.0"],
        ),
    )
    if model_source == "string_task":
        spec.tasks = ["task_name"]

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="mocked output"
        )
        _create_venv(
            spec=spec,
            base_dir=".",
            temp_dir=str(tmp_path),
            env=os.environ.copy(),
            dry_run=False,
            action=_test_action,
        )

    args = mock_run.call_args.args[0]
    assert args[:4] == ["uv", "pip", "install", "REGISTERED_Acme==2.0"]
    assert "registered-acme==1.0" not in args
    assert "acme-core==1.0" not in args


def test_824_provider_override_preserves_independent_dependencies(
    registered_acme_distribution: Path,
) -> None:
    import_module("registered_acme")
    spec = FlowSpec(
        tasks=[FlowTask(name="acme-core/task", model="registered-acme/example")]
    )

    assert collect_auto_dependencies(spec, exclude_packages=["registered-acme"]) == [
        "acme-core==1.0"
    ]
    assert collect_auto_dependencies(spec, exclude_packages=["acme-core"]) == [
        "registered-acme==1.0"
    ]


def test_824_registration_distribution_override(
    registered_acme_distribution: Path,
) -> None:
    renamed = registered_acme_distribution.with_name("registered_plugin-1.0.dist-info")
    registered_acme_distribution.rename(renamed)
    (renamed / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: registered-plugin\nVersion: 1.0\n"
    )
    import_module("registered_acme")
    spec = FlowSpec(tasks=[FlowTask(model="registered-acme/example")])

    assert collect_auto_dependencies(spec) == ["acme-core==1.0", "registered-plugin==1.0"]
    assert collect_auto_dependencies(spec, exclude_packages=["REGISTERED_Plugin"]) == []


@pytest.mark.parametrize(
    ("provider_name", "expected"),
    [("acme-models", "acme-models==1.0"), ("custom-acme", "custom-acme")],
)
def test_824_model_provider_without_ownership_manifest(
    acme_distribution: Path, provider_name: str, expected: str
) -> None:
    unrelated = acme_distribution.parent / "acme-9.0.dist-info"
    unrelated.mkdir()
    (unrelated / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: acme\nVersion: 9.0\n"
    )
    (unrelated / "top_level.txt").write_text("acme\n")
    assert distribution("acme").files is None
    import_module("acme.installed")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    assert get_model(f"{provider_name}/example", memoize=False).name == "example"
    assert collect_auto_dependencies(spec) == [expected]
    assert collect_auto_dependencies(spec, exclude_packages=["acme"]) == [expected]


@pytest.mark.parametrize(
    ("distribution_name", "top_level"),
    [("acme-models", True), ("acme", False), ("acme-models", False)],
)
@pytest.mark.parametrize("provider_name", ["editable-acme", "acme-models", "lazy-acme"])
@pytest.mark.parametrize("conflicting_distribution", [False, True])
def test_824_editable_model_provider_distribution(
    acme_distribution: Path,
    tmp_path: Path,
    distribution_name: str,
    top_level: bool,
    provider_name: str,
    conflicting_distribution: bool,
) -> None:
    acme_distribution = acme_distribution.rename(
        acme_distribution.with_name(
            f"{distribution_name.replace('-', '_')}-1.0.dist-info"
        )
    )
    (acme_distribution / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {distribution_name}\nVersion: 1.0\n"
    )
    project = tmp_path / distribution_name
    project.mkdir()
    shutil.move(str(acme_distribution.parent / "acme"), str(project / "acme"))
    _make_editable_distribution(acme_distribution, project, project)
    if not top_level:
        (acme_distribution / "top_level.txt").unlink()
        assert "acme" not in packages_distributions()
    if conflicting_distribution:
        other_dist_info = acme_distribution.parent / "other_acme-2.0.dist-info"
        other_dist_info.mkdir()
        (other_dist_info / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: other-acme\nVersion: 2.0\n"
        )
        (other_dist_info / "top_level.txt").write_text("acme\n")
        if not top_level:
            assert packages_distributions()["acme"] == ["other-acme"]
    addsitedir(str(acme_distribution.parent))
    # Inspect checks editable metadata using the import name, so differing
    # distribution names can leave a resolvable provider without a namespace.
    editable = import_module("acme.editable")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    assert collect_auto_dependencies(spec) == [f"-e {project}"]
    assert (
        collect_auto_dependencies(
            spec, exclude_packages=[distribution_name.upper().replace("-", "_")]
        )
        == []
    )
    assert editable.instances == []
    assert editable.factory_calls == []
    # Each parameter imports a fresh provider class, so bypass cached models.
    assert get_model(f"{provider_name}/example", memoize=False).name == "example"
    assert len(editable.instances) == 1
    assert bool(editable.factory_calls) == (provider_name == "lazy-acme")


def _make_editable_distribution(
    dist_info: Path, project: Path, import_path: Path
) -> None:
    pth_name = f"{dist_info.name}.pth"
    (dist_info.parent / pth_name).write_text(f"{import_path}\n")
    (dist_info / "direct_url.json").write_text(
        json.dumps({"url": project.as_uri(), "dir_info": {"editable": True}})
    )
    (dist_info / "RECORD").write_text(
        f"{pth_name},,\n"
        f"{dist_info.name}/METADATA,,\n"
        f"{dist_info.name}/direct_url.json,,\n"
        f"{dist_info.name}/RECORD,,\n"
    )


@pytest.fixture
def editable_acme_project(acme_distribution: Path, tmp_path: Path) -> Path:
    project = tmp_path / "repo" / "models"
    project.mkdir(parents=True)
    shutil.move(str(acme_distribution.parent / "acme"), str(project / "acme"))
    _make_editable_distribution(acme_distribution, project, project)
    addsitedir(str(acme_distribution.parent))
    return project


@pytest.mark.parametrize("provider_name", ["acme-models", "editable-acme", "lazy-acme"])
def test_824_editable_model_provider_overlapping_project_roots(
    acme_distribution: Path, editable_acme_project: Path, provider_name: str
) -> None:
    unrelated = acme_distribution.parent / "acme-9.0.dist-info"
    unrelated.mkdir()
    (unrelated / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: acme\nVersion: 9.0\n"
    )
    (unrelated / "top_level.txt").write_text("acme\n")
    other_source = editable_acme_project.parent / "other-src"
    other_source.mkdir()
    _make_editable_distribution(unrelated, editable_acme_project.parent, other_source)
    addsitedir(str(acme_distribution.parent))
    import_module("acme.editable")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    assert get_model(f"{provider_name}/example", memoize=False).name == "example"
    assert collect_auto_dependencies(spec) == [f"-e {editable_acme_project}"]
    assert collect_auto_dependencies(spec, exclude_packages=["acme"]) == [
        f"-e {editable_acme_project}"
    ]


@pytest.mark.parametrize("provider_name", ["acme-models", "editable-acme", "lazy-acme"])
@pytest.mark.parametrize("symlink", [False, True])
def test_824_editable_model_provider_import_path_ownership(
    acme_distribution: Path,
    tmp_path: Path,
    provider_name: str,
    symlink: bool,
) -> None:
    project = tmp_path / "repo" / "model-project"
    source = project / "src"
    source.mkdir(parents=True)
    shutil.move(str(acme_distribution.parent / "acme"), str(source / "acme"))
    import_path = source
    if symlink:
        import_path = project / "build" / "__editable__.acme_models"
        (import_path / "acme").mkdir(parents=True)
        for path in (source / "acme").glob("*.py"):
            (import_path / "acme" / path.name).symlink_to(path)
    _make_editable_distribution(acme_distribution, project, import_path)
    unrelated = acme_distribution.parent / "acme-9.0.dist-info"
    unrelated.mkdir()
    (unrelated / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: acme\nVersion: 9.0\n"
    )
    (unrelated / "top_level.txt").write_text("acme\n")
    _make_editable_distribution(unrelated, project.parent, project.parent)
    addsitedir(str(acme_distribution.parent))
    editable = import_module("acme.editable")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    assert editable.__file__ == str(import_path / "acme" / "editable.py")
    assert get_model(f"{provider_name}/example", memoize=False).name == "example"
    assert collect_auto_dependencies(spec) == [f"-e {project}"]


@pytest.mark.parametrize("provider_name", ["acme-models", "editable-acme", "lazy-acme"])
@pytest.mark.parametrize("package_dir", ["acme", "implementation", "module"])
@pytest.mark.parametrize("finder_manifest", [True, False])
def test_824_editable_model_provider_import_finder(
    acme_distribution: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    package_dir: str,
    finder_manifest: bool,
) -> None:
    project = tmp_path / "repo" / "models"
    project.mkdir(parents=True)
    shutil.move(str(acme_distribution.parent / "acme"), str(project / package_dir))
    _make_editable_distribution(acme_distribution, project, project)
    (acme_distribution / "top_level.txt").unlink()
    fixtures = Path(__file__).parent / "model_providers"
    shutil.copyfile(
        fixtures / "acme_finder.pth",
        acme_distribution.parent / f"{acme_distribution.name}.pth",
    )
    shutil.copyfile(
        fixtures / "acme_finder.py", acme_distribution.parent / "acme_finder.py"
    )
    mapping = {"acme": str(project / package_dir)}
    if package_dir == "module":
        (acme_distribution.parent / "acme").mkdir()
        shutil.copyfile(
            fixtures / "acme" / "__init__.py",
            acme_distribution.parent / "acme" / "__init__.py",
        )
        mapping = {"acme.editable": str(project / package_dir / "editable")}
    (acme_distribution.parent / "acme_finder.json").write_text(json.dumps(mapping))
    if finder_manifest:
        with (acme_distribution / "RECORD").open("a") as record:
            record.write("acme_finder.py,,\nacme_finder.json,,\n")
    monkeypatch.setattr(sys, "meta_path", sys.meta_path.copy())
    addsitedir(str(acme_distribution.parent))
    editable = import_module("acme.editable")
    finder = import_module("acme_finder")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    expected = (
        f"-e {project}"
        if finder_manifest or provider_name == "acme-models"
        else provider_name
    )
    assert collect_auto_dependencies(spec) == [expected]
    assert finder.install_calls == 1
    assert editable.instances == []
    assert editable.factory_calls == []
    assert get_model(f"{provider_name}/example", memoize=False).name == "example"


@pytest.mark.parametrize("provider_name", ["acme-models", "editable-acme"])
def test_824_model_provider_undecodable_pth(
    acme_distribution: Path, editable_acme_project: Path, provider_name: str
) -> None:
    unrelated = acme_distribution.parent / "unrelated-1.0.dist-info"
    unrelated.mkdir()
    (unrelated / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: unrelated\nVersion: 1.0\n"
    )
    _make_editable_distribution(unrelated, editable_acme_project.parent, unrelated)
    (unrelated.parent / f"{unrelated.name}.pth").write_bytes(b"/repo/caf\xe9\n")
    import_module("acme.editable")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    assert get_model(f"{provider_name}/example", memoize=False).name == "example"
    assert collect_auto_dependencies(spec) == [f"-e {editable_acme_project}"]


@pytest.mark.parametrize("provider_name", ["acme-models", "editable-acme"])
@pytest.mark.parametrize("read_error", [PermissionError, FileNotFoundError])
def test_824_model_provider_unreadable_pth(
    acme_distribution: Path,
    editable_acme_project: Path,
    provider_name: str,
    read_error: type[OSError],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (acme_distribution / "top_level.txt").unlink()
    unrelated = acme_distribution.parent / "unrelated-1.0.dist-info"
    unrelated.mkdir()
    (unrelated / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: unrelated\nVersion: 1.0\n"
    )
    _make_editable_distribution(unrelated, editable_acme_project.parent, unrelated)
    unreadable = unrelated.parent / f"{unrelated.name}.pth"
    open_file = Path.open

    def open_with_error(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == unreadable:
            raise read_error(str(path))
        return open_file(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_with_error)
    import_module("acme.editable")
    spec = FlowSpec(tasks=[FlowTask(model=f"{provider_name}/example")])

    assert get_model(f"{provider_name}/example", memoize=False).name == "example"
    assert collect_auto_dependencies(spec) == [f"-e {editable_acme_project}"]


def test_824_model_distribution_refreshed_per_collection(
    acme_distribution: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import_module("acme.installed")
    monkeypatch.setenv("INSPECT_EVAL_MODEL", "custom-acme/default")
    spec = FlowSpec(
        tasks=[
            FlowTask(
                model=f"acme-models/example-{i}",
                model_roles={"grader": f"custom-acme/grader-{i}"},
            )
            for i in range(100)
        ]
        + [FlowTask() for _ in range(100)]
    )
    assert collect_auto_dependencies(spec) == ["acme-models==1.0"]

    shutil.rmtree(acme_distribution)
    assert collect_auto_dependencies(spec) == ["acme-models", "custom-acme"]


def test_824_builtin_models_do_not_scan_distributions() -> None:
    spec = FlowSpec(tasks=[FlowTask(model="openai/example")])
    with patch("inspect_flow._launcher.auto_dependencies.distributions") as scan:
        assert collect_auto_dependencies(spec) == [get_pip_string("openai")]
        scan.assert_not_called()


@pytest.mark.parametrize("packages", [["other-acme"], ["acme-models", "other-acme"]])
def test_824_model_provider_unowned_distribution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, packages: list[str]
) -> None:
    for package in packages:
        dist_info = tmp_path / f"{package.replace('-', '_')}-1.0.dist-info"
        dist_info.mkdir()
        (dist_info / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {package}\nVersion: 1.0\n"
        )
        (dist_info / "top_level.txt").write_text("acme\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    def provider() -> None:
        pass

    registry_add(provider, RegistryInfo(type="modelapi", name="acme/custom-acme"))
    spec = FlowSpec(tasks=[FlowTask(model="custom-acme/example")])

    assert collect_auto_dependencies(spec) == ["custom-acme"]


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("cf/some-model", ["openai"]),
        ("unknown-provider/some-model", ["unknown-provider"]),
        ("bare-model", []),
    ],
)
def test_818_model_provider_dependency_fallbacks(
    model: str, expected: list[str]
) -> None:
    spec = FlowSpec(tasks=[FlowTask(model=model)])

    assert collect_auto_dependencies(spec) == [
        get_pip_string(package) for package in expected
    ]


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
            assert install_req_args == [
                "uv",
                "pip",
                "install",
                "-r",
                req_file.as_posix(),
            ]

            last_args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert last_args == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
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

            assert mock_run.call_count == 2

            last_args = mock_run.call_args.args[0]
            flow_path = str((Path(__file__).parents[1]).resolve())
            assert last_args == [
                "uv",
                "pip",
                "install",
                f"-e {flow_path}",
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
