from logging import getLogger
from typing import Sequence

from inspect_ai._util.registry import (
    registry_find,
    registry_info,
    registry_package_name,
)
from inspect_ai.util import SandboxEnvironmentType
from inspect_ai.util._sandbox.registry import registry_match_sandboxenv

from inspect_flow._launcher.pip_string import get_pip_string
from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowModel,
    FlowScorer,
    FlowSolver,
    FlowSpec,
    FlowTask,
    NotGiven,
)

logger = getLogger(__name__)

# TODO:ransom how do we keep in sync with inspect_ai - should probably export from there
_MODEL_PROVIDERS: dict[str, list[str]] = {
    "groq": ["groq"],
    "openai": ["openai"],
    "anthropic": ["anthropic"],
    "google": ["google-genai"],
    "hf": ["torch", "transformers", "accelerate"],
    "vllm": ["vllm"],
    "cf": [],
    "mistral": ["mistralai"],
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
}


def collect_auto_dependencies(spec: FlowSpec) -> list[str]:
    result = set()

    for task in spec.tasks or []:
        _collect_task_dependencies(task, result)

    # inspect_ai is already included by inspect-flow
    return sorted({get_pip_string(dep) for dep in result if dep != "inspect_ai"})


def _collect_task_dependencies(task: FlowTask | str, dependencies: set[str]) -> None:
    if isinstance(task, str):
        return _collect_name_dependencies(task, dependencies)

    _collect_name_dependencies(task.name, dependencies)
    _collect_maybe_sequence_dependencies(task.scorer, dependencies)
    _collect_maybe_sequence_dependencies(task.solver, dependencies)
    _collect_sandbox_dependencies(task.sandbox, dependencies)
    # Issue #262 _collect_approver_dependencies(task.approver, dependencies)

    if task.model:
        _collect_model_dependencies(task.model, dependencies)
    if task.model_roles:
        for model_role in task.model_roles.values():
            _collect_model_dependencies(model_role, dependencies)


def _collect_name_dependencies(
    name: str | None | NotGiven, dependencies: set[str]
) -> None:
    if not name or name.find("@") != -1 or name.find(".py") != -1:
        # Looks like a file name, not a package name
        return
    split = name.split("/", maxsplit=1)
    if len(split) == 2:
        dependencies.add(split[0])


def _collect_model_dependencies(
    model: str | FlowModel | None, dependencies: set[str]
) -> None:
    name = model.name if isinstance(model, FlowModel) else model
    if not name:
        return
    split = name.split("/", maxsplit=1)
    if len(split) == 2:
        dependencies.update(_MODEL_PROVIDERS.get(split[0], [split[0]]))


def _collect_maybe_sequence_dependencies(
    solver: str
    | FlowSolver
    | FlowScorer
    | Sequence[str | FlowSolver | FlowScorer]
    | FlowAgent
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
    _collect_name_dependencies(solver.name, dependencies)


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
