from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from inspect_ai import ScannerConfig, Task
from inspect_ai._util.registry import is_registry_object, registry_value
from inspect_ai.model import Model
from inspect_ai.scorer import Scorer
from pydantic_core import to_jsonable_python

from inspect_flow._runner.scanner import is_scanner_spec
from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowFactory,
    FlowModel,
    FlowScorer,
    FlowSolver,
    FlowSpec,
    FlowStoreConfig,
    FlowTask,
)
from inspect_flow._util.not_given import default_none, is_set

_TASK_MESSAGE = "You provided an already-instantiated Task object, which cannot be serialized and recreated in another process. Fix: use FlowTask with a registry or file task name."
_MODEL_MESSAGE = "You provided an already-instantiated Model object, which cannot be serialized and recreated in another process. Fix: use FlowModel or a model name string."
_SCORER_MESSAGE = "You provided an already-instantiated Scorer object, which cannot be serialized and recreated in another process. Fix: use FlowScorer or a scorer name string."
_SOLVER_MESSAGE = "You provided an already-instantiated Solver or Agent object, which cannot be serialized and recreated in another process. Fix: use FlowSolver, FlowAgent, or a name string."
_EARLY_STOPPING_MESSAGE = "early_stopping holds live callback objects, which cannot be serialized and recreated in another process. Fix: remove early_stopping from portable specs."
_SCANNER_MESSAGE = 'The ScannerConfig has scanners that are not serializable spec references (e.g. already-instantiated Scanner objects), which cannot be serialized and recreated in another process. Fix: set options.scanner to a path to a scanner config file or use scanner spec references (e.g. {"name": "keyword_scanner"}).'
_SCANNER_MODEL_MESSAGE = "You provided an already-instantiated Model object as the ScannerConfig model or in model_roles, which cannot be serialized and recreated in another process. Fix: use a model name string."
_FACTORY_MESSAGE = "You provided a factory callable that cannot be recreated in another process (e.g. a lambda, functools.partial, nested function, class, or callable object). Fix: use a registry name or a module-level function."
_FILTER_MESSAGE = "You provided a store filter callable that cannot be recreated in another process (e.g. a lambda, functools.partial, nested function, class, or callable object). Fix: use a registered filter name or a module-level function."
_VALUES_MESSAGE = "This field contains a value that cannot be serialized and recreated in another process (e.g. a live Inspect object or a non-reconstructable callable). Fix: use only JSON-serializable data, registry references, or module-level callables."


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

    def __reduce__(
        self,
    ) -> tuple[type["SpecNotPortableError"], tuple[list[SpecViolation], str | None]]:
        # The default exception reduce replays __init__ with self.args (the
        # rendered message), which would corrupt violations on unpickling.
        return (type(self), (self.violations, self.hint))


def validate_portable_spec(spec: FlowSpec) -> None:
    """Validate that a flow spec can be serialized and recreated in another process.

    A spec is portable when every task, model, solver, scorer, agent, and
    scanner it references is a spec/registry reference rather than a live
    (already-instantiated) Inspect object. Portable specs can cross a
    YAML/JSON boundary, e.g. venv execution or submission to a remote
    orchestrator. Factory callables are allowed only when reconstructable —
    a registry object or a module-level function; lambdas, partials, nested
    functions, and callable objects are rejected. Free-form value containers
    (`args`, `extra_args`, `metadata`, `flow_metadata`, scanner params) are
    inspected too: any leaf that serializes lossily is rejected, while
    JSON-serializable data, natively-serialized types, and registry
    references are accepted. The spec is not expanded or resolved, and
    nothing is installed or launched.

    Two limitations: specs pulled in via `includes` are not descended into
    (validate a resolved spec, after includes are merged, to cover them),
    and a value whose type Pydantic silently coerces on dump (e.g. a
    `datetime` becoming an ISO string) round-trips as the coerced type
    rather than being flagged.

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
        for scalar, prefix, name in (
            (defaults.model, defaults.model_prefix, "model"),
            (defaults.solver, defaults.solver_prefix, "solver"),
            (defaults.agent, defaults.agent_prefix, "agent"),
        ):
            if is_set(scalar):
                _check_wrapper(scalar, f"defaults.{name}", violations)
            for key, wrapper in (default_none(prefix) or {}).items():
                _check_wrapper(wrapper, f"defaults.{name}_prefix[{key!r}]", violations)
    _check_values(spec.flow_metadata, "flow_metadata", violations)
    if is_set(spec.options):
        _check_values(spec.options.metadata, "options.metadata", violations)
    _check_scanner(spec, violations)
    _check_store(spec, violations)
    if violations:
        raise SpecNotPortableError(violations)


def _entries(value: Any, path: str) -> list[tuple[str, Any]]:
    if not value:
        return []
    if isinstance(value, Mapping):
        return [(f"{path}[{key!r}]", entry) for key, entry in value.items()]
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [(f"{path}[{i}]", entry) for i, entry in enumerate(value)]
    return [(path, value)]


def _is_reconstructable(value: Any) -> bool:
    # Mirrors callable_name in _util.pydantic_util: a non-registry callable is
    # only reconstructable if it round-trips as `<file>@<name>`, i.e. it has a
    # __code__, a real name (not a lambda), and is reachable as a module-level
    # attribute (__qualname__ == __name__, ruling out nested funcs and methods).
    if not callable(value) or is_registry_object(value):
        return True
    code = getattr(value, "__code__", None)
    return (
        code is not None
        and value.__name__ != "<lambda>"
        and getattr(value, "__qualname__", value.__name__) == value.__name__
    )


def _round_trips(obj: Any) -> bool:
    # Mirrors _serialize_fallback: an object that reaches the dump fallback
    # round-trips only if it becomes a registry dict or a resolvable callable
    # name; anything else serializes to a lossy repr.
    value = registry_value(obj)
    if isinstance(value, dict):
        return True
    if callable(value):
        return _is_reconstructable(value)
    return False


def _check_values(value: Any, path: str, violations: list[SpecViolation]) -> None:
    if not is_set(value):
        return
    coerced: list[Any] = []
    to_jsonable_python(value, fallback=coerced.append)
    if any(not _round_trips(obj) for obj in coerced):
        violations.append(SpecViolation(path, _VALUES_MESSAGE))


def _check_factory(factory: Any, path: str, violations: list[SpecViolation]) -> None:
    inner = factory.factory if isinstance(factory, FlowFactory) else factory
    if not _is_reconstructable(inner):
        violations.append(SpecViolation(f"{path}.factory", _FACTORY_MESSAGE))
    if isinstance(factory, FlowFactory):
        _check_values(factory.args, f"{path}.factory.args", violations)


def _check_wrapper(wrapper: Any, path: str, violations: list[SpecViolation]) -> None:
    _check_factory(wrapper.factory, path, violations)
    for field in ("args", "model_args", "flow_metadata"):
        _check_values(getattr(wrapper, field, None), f"{path}.{field}", violations)


def _check_task(task: FlowTask, path: str, violations: list[SpecViolation]) -> None:
    _check_factory(task.factory, path, violations)
    _check_values(task.args, f"{path}.args", violations)
    _check_values(task.extra_args, f"{path}.extra_args", violations)
    _check_values(task.metadata, f"{path}.metadata", violations)
    _check_values(task.flow_metadata, f"{path}.flow_metadata", violations)
    if isinstance(task.model, Model):
        violations.append(SpecViolation(f"{path}.model", _MODEL_MESSAGE))
    elif isinstance(task.model, FlowModel):
        _check_wrapper(task.model, f"{path}.model", violations)
    for role, model in (default_none(task.model_roles) or {}).items():
        if isinstance(model, Model):
            violations.append(
                SpecViolation(f"{path}.model_roles[{role!r}]", _MODEL_MESSAGE)
            )
        elif isinstance(model, FlowModel):
            _check_wrapper(model, f"{path}.model_roles[{role!r}]", violations)
    for scorer_path, scorer in _entries(task.scorer, f"{path}.scorer"):
        if isinstance(scorer, Scorer):
            violations.append(SpecViolation(scorer_path, _SCORER_MESSAGE))
        elif isinstance(scorer, FlowScorer):
            _check_wrapper(scorer, scorer_path, violations)
    for solver_path, solver in _entries(task.solver, f"{path}.solver"):
        if not isinstance(solver, (str, FlowSolver, FlowAgent)):
            violations.append(SpecViolation(solver_path, _SOLVER_MESSAGE))
        elif isinstance(solver, (FlowSolver, FlowAgent)):
            _check_wrapper(solver, solver_path, violations)
    if is_set(task.early_stopping):
        violations.append(
            SpecViolation(f"{path}.early_stopping", _EARLY_STOPPING_MESSAGE)
        )


def _check_scanner(spec: FlowSpec, violations: list[SpecViolation]) -> None:
    scanner = default_none(spec.options.scanner) if spec.options else None
    if isinstance(scanner, ScannerConfig):
        for path, entry in _entries(scanner.scanners, "options.scanner.scanners"):
            if not is_scanner_spec(entry):
                violations.append(SpecViolation(path, _SCANNER_MESSAGE))
            else:
                params = (
                    entry.get("params")
                    if isinstance(entry, dict)
                    else getattr(entry, "params", None)
                )
                _check_values(params, f"{path}.params", violations)
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


def _check_store(spec: FlowSpec, violations: list[SpecViolation]) -> None:
    store = default_none(spec.store)
    if isinstance(store, FlowStoreConfig):
        for filter_path, entry in _entries(store.filter, "store.filter"):
            if not _is_reconstructable(entry):
                violations.append(SpecViolation(filter_path, _FILTER_MESSAGE))
