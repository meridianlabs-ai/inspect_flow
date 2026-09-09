import os
from logging import getLogger
from typing import Any, Callable, Collection, Sequence

from inspect_ai import Task
from inspect_ai._util.registry import (
    registry_find,
    registry_info,
    registry_package_name,
    registry_unqualified_name,
)
from inspect_ai.agent import Agent
from inspect_ai.scorer import Scorer
from inspect_ai.solver import Solver
from inspect_ai.util import SandboxEnvironmentType
from inspect_ai.util._sandbox.registry import registry_match_sandboxenv
from packaging.utils import canonicalize_name

from inspect_flow._config.model_refs import effective_ref, iter_model_refs
from inspect_flow._launcher.pip_string import get_pip_string
from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowFactory,
    FlowScorer,
    FlowSolver,
    FlowSpec,
    FlowTask,
    NotGiven,
)
from inspect_flow._util.pydantic_util import callable_name, is_nameable_callable

logger = getLogger(__name__)

# TODO:ransom how do we keep in sync with inspect_ai - should probably export from there
_MODEL_PROVIDERS: dict[str, list[str]] = {
    "groq": ["groq"],
    "openai": ["openai"],
    "anthropic": ["anthropic"],
    "google": ["google-genai"],
    "hf": ["torch", "transformers", "accelerate"],
    "vllm": ["vllm"],
    "cf": ["openai"],  # renamed to "cloudflare" in inspect-ai 0.3.248
    "cloudflare": ["openai"],
    "mistral": ["mistralai"],
    "moonshot": ["openai"],  # added in inspect-ai 0.3.249
    "grok": ["xai_sdk"],
    "together": ["openai"],
    "fireworks": ["openai"],
    "sambanova": ["openai"],
    "ollama": ["openai"],
    "openrouter": ["openai"],
    "perplexity": ["openai"],
    "llama-cpp-python": ["openai"],
    "azureai": ["azure-ai-inference"],
    "bedrock": [],
    "sglang": ["openai"],
    "transformer_lens": ["transformer_lens"],
    "hf-inference-providers": ["openai"],
    "mockllm": [],
    "openai-api": ["openai"],
    "openai-api-completions": ["openai"],
    # Starts a local vllm server when no endpoint is configured, like "vllm"
    "vllm-completions": ["vllm"],
    "deepseek": ["openai"],
    "sagemaker": ["openai"],  # boto3/aioboto3 ship with inspect-ai
    "nnterp": ["nnterp"],
    "none": [],
}


def collect_auto_dependencies(
    spec: FlowSpec, exclude_packages: Collection[str] = ()
) -> list[str]:
    result = set()

    for task in spec.tasks or []:
        _collect_task_dependencies(task, result)
    for ref in iter_model_refs(spec):
        # fallback_models are provider-native ids, so they name no provider
        if ref.name and ref.kind != "fallback":
            _collect_model_dependencies(ref.name, result)

    # An explicit pin must win over the auto-detected host version of the same
    # package, so drop any package the user named directly. Its version
    # requirement (and whatever uv resolves from it) then governs instead.
    exclude = {canonicalize_name(p) for p in exclude_packages}

    # inspect_ai is already included by inspect-flow
    return sorted(
        {
            get_pip_string(dep)
            for dep in result
            if dep != "inspect_ai" and canonicalize_name(dep) not in exclude
        }
    )


def _collect_task_dependencies(
    task: Task | FlowTask | str, dependencies: set[str]
) -> None:
    assert not isinstance(task, Task), (
        "validate_portable_spec should have ensured no Task instances"
    )
    if isinstance(task, str):
        _collect_env_model_dependencies(dependencies)
        return _collect_name_dependencies(task, dependencies)

    _collect_name_dependencies(_effective_name(task.name, task.factory), dependencies)
    _collect_maybe_sequence_dependencies(task.scorer, dependencies)
    _collect_maybe_sequence_dependencies(task.solver, dependencies)
    _collect_sandbox_dependencies(task.sandbox, dependencies)
    # Issue #262 _collect_approver_dependencies(task.approver, dependencies)

    if not task.model and not task.model_roles:
        _collect_env_model_dependencies(dependencies)


def _collect_env_model_dependencies(
    dependencies: set[str],
) -> None:
    if env_model := os.getenv("INSPECT_EVAL_MODEL"):
        _collect_model_dependencies(env_model, dependencies)


def _effective_name(
    name: str | None | NotGiven,
    factory: FlowFactory[Any] | Callable[..., Any] | str | None | NotGiven,
) -> str | None:
    # A registry callable is serialized as its pkg/name and resolved in the
    # child through the registry, so its package is knowable; no other callable
    # can be installed statically.
    ref = effective_ref(name, factory)
    if callable(ref):
        return callable_name(ref) if is_nameable_callable(ref) else None
    return ref


def _collect_name_dependencies(
    name: str | None | NotGiven, dependencies: set[str]
) -> None:
    if not name or name.find("@") != -1 or name.find(".py") != -1:
        # Looks like a file name, not a package name
        return
    split = name.split("/", maxsplit=1)
    if len(split) == 2:
        dependencies.add(split[0])


def _collect_model_dependencies(name: str, dependencies: set[str]) -> None:
    split = name.split("/", maxsplit=1)
    if len(split) == 2:
        provider = split[0]
        entries = registry_find(
            lambda info: (
                info.type == "modelapi" and registry_unqualified_name(info) == provider
            )
        )
        if entries:
            package = registry_package_name(registry_info(entries[0]).name)
            if package and package != "inspect_ai":
                dependencies.add(package)
                return
        # Built-in providers still need the SDK dependencies from the table.
        dependencies.update(_MODEL_PROVIDERS.get(provider, [provider]))


def _collect_maybe_sequence_dependencies(
    solver: str
    | FlowSolver
    | FlowScorer
    | Sequence[str | FlowSolver | FlowScorer | Solver | Scorer]
    | FlowAgent
    | Solver
    | Scorer
    | Agent
    | None
    | NotGiven,
    dependencies: set[str],
) -> None:
    if not solver:
        return
    if isinstance(solver, str):
        return _collect_name_dependencies(solver, dependencies)
    if isinstance(solver, Sequence):
        for s in solver:
            _collect_maybe_sequence_dependencies(s, dependencies)
        return
    assert isinstance(solver, (FlowSolver, FlowScorer, FlowAgent)), (
        "validate_portable_spec should have ensured no Solver, Scorer, or Agent instances"
    )
    _collect_name_dependencies(
        _effective_name(solver.name, solver.factory), dependencies
    )


def _collect_sandbox_dependencies(
    sandbox: SandboxEnvironmentType | None | NotGiven,
    dependencies: set[str],
) -> None:
    if not sandbox:
        return
    if isinstance(sandbox, str):
        return _collect_sandbox_type_dependencies(sandbox, dependencies)
    if isinstance(sandbox, tuple):
        return _collect_sandbox_type_dependencies(sandbox[0], dependencies)
    return _collect_sandbox_type_dependencies(sandbox.type, dependencies)


def _collect_sandbox_type_dependencies(
    sandbox_type: str,
    dependencies: set[str],
) -> None:
    entries = registry_find(registry_match_sandboxenv(sandbox_type))
    if not entries:
        logger.warning(
            f"No matching sandbox environment found in registry for {sandbox_type}"
        )
        return
    info = registry_info(entries[0])
    name = registry_package_name(info.name)
    assert name
    dependencies.add(name)
