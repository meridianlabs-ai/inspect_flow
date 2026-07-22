from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from inspect_ai import ScannerConfig, Task
from inspect_ai.model import Model
from inspect_ai.scorer import Scorer

from inspect_flow._runner.scanner import is_scanner_spec, scanner_entries
from inspect_flow._types.flow_types import FlowAgent, FlowSolver, FlowSpec, FlowTask
from inspect_flow._util.not_given import default_none, is_set

_TASK_MESSAGE = "You provided an already-instantiated Task object, which cannot be serialized and recreated in another process. Fix: use FlowTask with a registry or file task name."
_MODEL_MESSAGE = "You provided an already-instantiated Model object, which cannot be serialized and recreated in another process. Fix: use FlowModel or a model name string."
_SCORER_MESSAGE = "You provided an already-instantiated Scorer object, which cannot be serialized and recreated in another process. Fix: use FlowScorer or a scorer name string."
_SOLVER_MESSAGE = "You provided an already-instantiated Solver or Agent object, which cannot be serialized and recreated in another process. Fix: use FlowSolver, FlowAgent, or a name string."
_EARLY_STOPPING_MESSAGE = "early_stopping holds live callback objects, which cannot be serialized and recreated in another process. Fix: remove early_stopping from portable specs."
_SCANNER_MESSAGE = 'The ScannerConfig has scanners that are not serializable spec references (e.g. already-instantiated Scanner objects), which cannot be serialized and recreated in another process. Fix: set options.scanner to a path to a scanner config file or use scanner spec references (e.g. {"name": "keyword_scanner"}).'
_SCANNER_MODEL_MESSAGE = "You provided an already-instantiated Model object as the ScannerConfig model or in model_roles, which cannot be serialized and recreated in another process. Fix: use a model name string."


@dataclass
class SpecViolation:
    """A single reason a flow spec is not portable.

    Attributes:
        path: Field path of the offending value (e.g. `"tasks[2].model_roles['grader']"`).
        message: What is wrong and the portable alternative to use.
    """

    path: str
    message: str


class SpecNotPortableError(ValueError):
    """Raised when a flow spec cannot be serialized and recreated in another process.

    Attributes:
        violations: Every violation found, each with its field path.
        hint: Optional extra guidance appended to the rendered message.
    """

    def __init__(
        self, violations: list[SpecViolation], hint: str | None = None
    ) -> None:
        self.violations = violations
        self.hint = hint
        lines = [
            "The flow spec is not portable: it cannot be serialized and recreated in another Python process."
        ]
        lines.extend(f"- {v.path}: {v.message}" for v in violations)
        if hint:
            lines.append(hint)
        super().__init__("\n".join(lines))


def validate_portable_spec(spec: FlowSpec) -> None:
    """Validate that a flow spec can be serialized and recreated in another process.

    A spec is portable when every task, model, solver, scorer, agent, and
    scanner it references is a spec/registry reference rather than a live
    (already-instantiated) Inspect object. Portable specs can cross a
    YAML/JSON boundary, e.g. venv execution or submission to a remote
    orchestrator. Factory callables are allowed (they serialize as registry
    or file references). The spec is not expanded or resolved, and nothing
    is installed or launched.

    Args:
        spec: The flow spec to validate.

    Raises:
        SpecNotPortableError: If the spec references live objects. The
            error's `violations` list the field path and problem for every
            offending field.
    """
    violations: list[SpecViolation] = []
    for index, task in enumerate(spec.tasks or []):
        path = f"tasks[{index}]"
        if isinstance(task, Task):
            violations.append(SpecViolation(path, _TASK_MESSAGE))
        elif isinstance(task, FlowTask):
            _check_task(task, path, violations)
    defaults = default_none(spec.defaults)
    if defaults:
        if is_set(defaults.task):
            _check_task(defaults.task, "defaults.task", violations)
        for key, template in (default_none(defaults.task_prefix) or {}).items():
            _check_task(template, f"defaults.task_prefix[{key!r}]", violations)
    _check_scanner(spec, violations)
    if violations:
        raise SpecNotPortableError(violations)


def _entries(value: Any, path: str) -> list[tuple[str, Any]]:
    if not value:
        return []
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [(f"{path}[{i}]", entry) for i, entry in enumerate(value)]
    return [(path, value)]


def _check_task(task: FlowTask, path: str, violations: list[SpecViolation]) -> None:
    if isinstance(task.model, Model):
        violations.append(SpecViolation(f"{path}.model", _MODEL_MESSAGE))
    for role, model in (default_none(task.model_roles) or {}).items():
        if isinstance(model, Model):
            violations.append(
                SpecViolation(f"{path}.model_roles[{role!r}]", _MODEL_MESSAGE)
            )
    for scorer_path, scorer in _entries(task.scorer, f"{path}.scorer"):
        if isinstance(scorer, Scorer):
            violations.append(SpecViolation(scorer_path, _SCORER_MESSAGE))
    for solver_path, solver in _entries(task.solver, f"{path}.solver"):
        if not isinstance(solver, (str, FlowSolver, FlowAgent)):
            violations.append(SpecViolation(solver_path, _SOLVER_MESSAGE))
    if is_set(task.early_stopping):
        violations.append(
            SpecViolation(f"{path}.early_stopping", _EARLY_STOPPING_MESSAGE)
        )


def _check_scanner(spec: FlowSpec, violations: list[SpecViolation]) -> None:
    scanner = default_none(spec.options.scanner) if spec.options else None
    for index, entry in enumerate(scanner_entries(scanner)):
        if not is_scanner_spec(entry):
            violations.append(
                SpecViolation(f"options.scanner.scanners[{index}]", _SCANNER_MESSAGE)
            )
    if isinstance(scanner, ScannerConfig):
        if isinstance(scanner.model, Model):
            violations.append(
                SpecViolation("options.scanner.model", _SCANNER_MODEL_MESSAGE)
            )
        for role, model in (scanner.model_roles or {}).items():
            if isinstance(model, Model):
                violations.append(
                    SpecViolation(
                        f"options.scanner.model_roles[{role!r}]",
                        _SCANNER_MODEL_MESSAGE,
                    )
                )
