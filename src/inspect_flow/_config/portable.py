from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from inspect_ai import Task
from inspect_ai._util.registry import is_registry_object, registry_info
from inspect_ai.model import Model
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from inspect_flow._types.flow_types import FlowSpec
from inspect_flow._util.pydantic_util import (
    MODEL_DUMP_ARGS,
    _serialize_fallback,
    survives_round_trip,
)

_PREAMBLE = "cannot be serialized and recreated in another process."
_TASK_MESSAGE = f"An already-instantiated Task object {_PREAMBLE} Fix: use FlowTask with a registry or file task name."
_MODEL_MESSAGE = f"An already-instantiated Model object {_PREAMBLE} Fix: use FlowModel or a model name string."
_SCORER_MESSAGE = f"An already-instantiated Scorer object {_PREAMBLE} Fix: use FlowScorer or a scorer name string."
_AGENT_MESSAGE = f"An already-instantiated Agent object {_PREAMBLE} Fix: use FlowAgent or an agent name string."
_SOLVER_MESSAGE = f"An already-instantiated Solver object {_PREAMBLE} Fix: use FlowSolver or a solver name string."
_CALLABLE_MESSAGE = f"A callable that cannot be named again {_PREAMBLE} Fix: use a registry name or a module-level function (not a lambda, functools.partial, nested function, class, or callable object)."
_VALUE_MESSAGE = f"This value {_PREAMBLE} Fix: use only JSON-serializable data, registry references, or module-level callables."

_REGISTRY_TYPE_MESSAGES = {
    "task": _TASK_MESSAGE,
    "modelapi": _MODEL_MESSAGE,
    "scorer": _SCORER_MESSAGE,
    "agent": _AGENT_MESSAGE,
    "solver": _SOLVER_MESSAGE,
}


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

    A portable spec survives the boundary the venv runner and remote
    orchestrators cross: dumped to YAML/JSON, then re-validated as a
    `FlowSpec` in a fresh process. Values that do not survive it are live
    (already-instantiated) Inspect objects such as `Task`, `Model`, `Scorer`,
    `Solver`, and `Agent` — which reload as a `repr` string or a plain dict
    rather than the object — and callables that cannot be named again, such
    as lambdas, `functools.partial`, nested functions, classes, and callable
    objects. Registry references and module-level functions are portable, as
    is any JSON-serializable data.

    Every field is checked, including free-form containers (`args`,
    `metadata`, `flow_metadata`, scanner params) and any spec listed in
    `includes`. The spec is not expanded or resolved, and nothing is
    installed or launched.

    One limitation: a value whose type Pydantic natively coerces on dump
    (e.g. a `datetime` becoming an ISO string) is reported as portable, since
    it reloads as the coerced type rather than being lost.

    Args:
        spec: The flow spec to validate.

    Raises:
        SpecNotPortableError: If the spec holds values that do not survive
            the boundary. The error's `violations` give the field path and
            problem for each one.
    """
    violations: list[SpecViolation] = []
    _walk(spec, "", violations)
    if violations:
        raise SpecNotPortableError(violations)


def _lossy(value: Any) -> bool:
    """Whether dumping this subtree coerces anything that cannot be reloaded."""
    coerced: list[Any] = []

    def record(obj: Any) -> Any:
        coerced.append(obj)
        try:
            # Serialize as the real dump would, so that pydantic keeps walking
            # into a coerced value (e.g. a registry dict) and reports what is
            # nested inside it too.
            return _serialize_fallback(obj)
        except Exception:
            # callable_name raises on callables with no __code__ (a partial or
            # callable object); the object is recorded, so it is still caught.
            return None

    try:
        if isinstance(value, BaseModel):
            value.model_dump(**{**MODEL_DUMP_ARGS, "fallback": record})
        else:
            to_jsonable_python(value, fallback=record)
    except Exception:
        return True
    return any(not survives_round_trip(obj) for obj in coerced)


def _children(value: Any) -> list[tuple[str, Any]]:
    """The addressable sub-values of a node, with the path segment for each."""
    if isinstance(value, BaseModel):
        # model_fields_set mirrors the dump's exclude_unset: an unset field is
        # not serialized, so it cannot carry a value across the boundary.
        return [(f".{name}", getattr(value, name)) for name in value.model_fields_set]
    if isinstance(value, Mapping):
        return [(f"[{key!r}]", item) for key, item in value.items()]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [(f"[{index}]", item) for index, item in enumerate(value)]
    return []


def _message(value: Any) -> str:
    # The registry's own type is the discriminator: Scorer/Solver/Agent are
    # runtime-checkable Protocols that any callable satisfies structurally, so
    # isinstance would label a lambda a Scorer.
    if is_registry_object(value):
        return _REGISTRY_TYPE_MESSAGES.get(registry_info(value).type, _VALUE_MESSAGE)
    if isinstance(value, Task):
        return _TASK_MESSAGE
    if isinstance(value, Model):
        return _MODEL_MESSAGE
    if callable(value):
        return _CALLABLE_MESSAGE
    return _VALUE_MESSAGE


def _walk(value: Any, path: str, violations: list[SpecViolation]) -> None:
    if not _lossy(value):
        return
    before = len(violations)
    for segment, child in _children(value):
        _walk(child, path + segment, violations)
    if len(violations) == before:
        # Nothing deeper accounts for it, so this node is the offending leaf.
        violations.append(SpecViolation(path.lstrip("."), _message(value)))
