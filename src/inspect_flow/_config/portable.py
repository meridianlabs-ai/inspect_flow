from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from inspect_ai import Task
from inspect_ai._util.registry import is_registry_object, registry_info
from inspect_ai.model import Model
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from inspect_flow._types.flow_types import FlowSpec, FlowTask
from inspect_flow._util.not_given import is_set
from inspect_flow._util.pydantic_util import (
    MODEL_DUMP_ARGS,
    serialize_fallback,
    serializes_to_registry_dict,
    survives_round_trip,
)

_PREAMBLE = "cannot be serialized and recreated in another process."
_TASK_MESSAGE = f"An already-instantiated Task object {_PREAMBLE} Fix: use FlowTask with a registry or file task name."
_MODEL_MESSAGE = f"An already-instantiated Model object {_PREAMBLE} Fix: use FlowModel or a model name string."
_SCORER_MESSAGE = f"An already-instantiated Scorer object {_PREAMBLE} Fix: use FlowScorer or a scorer name string."
_AGENT_MESSAGE = f"An already-instantiated Agent object {_PREAMBLE} Fix: use FlowAgent or an agent name string."
_SOLVER_MESSAGE = f"An already-instantiated Solver object {_PREAMBLE} Fix: use FlowSolver or a solver name string."
_CALLABLE_MESSAGE = f"A callable that cannot be named again {_PREAMBLE} Fix: use a registry name or a module-level function (not a lambda, functools.partial, nested function, class, or callable object)."
_SCANNER_MESSAGE = f'An already-instantiated Scanner object {_PREAMBLE} Fix: set options.scanner to a path to a scanner config file, or use scanner spec references (e.g. {{"name": "keyword_scanner"}}).'
_EARLY_STOPPING_MESSAGE = f"early_stopping holds live callback objects, which {_PREAMBLE} Fix: remove early_stopping from portable specs."
_VALUE_MESSAGE = f"This value {_PREAMBLE} Fix: use only JSON-serializable data, registry references, or module-level callables."

_REGISTRY_TYPE_MESSAGES = {
    "task": _TASK_MESSAGE,
    "modelapi": _MODEL_MESSAGE,
    "scorer": _SCORER_MESSAGE,
    "agent": _AGENT_MESSAGE,
    "solver": _SOLVER_MESSAGE,
    "scanner": _SCANNER_MESSAGE,
}

# Fields whose values the runner passes through `registry_kwargs`, which turns
# a registry dict back into the object. A live registered object survives the
# boundary in these positions, and only these.
_REINFLATED_FIELDS = frozenset({"args", "model_args", "extra_args"})

# Guard against a self-referential or pathologically nested value in a
# free-form container, which no amount of descending resolves.
_MAX_DEPTH = 100

# Stands in for a subtree pydantic refused to serialize outright, when nothing
# reached the fallback to blame.
_REFUSED = object()


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

    One limitation: a value Pydantic coerces natively on dump is reported as
    portable, because it reloads as the coerced type rather than being lost.
    The coercions that change what a task actually receives are `tuple` and
    `set` to `list`, a dataclass or `BaseModel` to `dict`, and non-string
    mapping keys to strings; `datetime`, `date`, `UUID`, `Path`, `Decimal`,
    and `bytes` become strings, and `NaN` becomes `None`.

    Args:
        spec: The flow spec to validate.

    Raises:
        SpecNotPortableError: If the spec holds values that do not survive
            the boundary. The error's `violations` give the field path and
            problem for each one.
    """
    violations: list[SpecViolation] = []
    _walk_early_stopping(spec, "", violations)
    _walk(spec, "", violations)
    if violations:
        raise SpecNotPortableError(violations)


def _walk_early_stopping(
    value: Any, path: str, violations: list[SpecViolation], depth: int = 0
) -> None:
    """Report every set `early_stopping`, wherever a FlowTask appears.

    This needs its own pass because the rule is invisible to the dump: an
    `EarlyStopping` implementation that pydantic serializes natively (a
    dataclass or BaseModel) reloads as a plain dict, silently losing the
    protocol, so `_walk` would prune the subtree as clean.
    """
    if depth > _MAX_DEPTH:
        return
    if isinstance(value, FlowTask) and is_set(value.early_stopping):
        violations.append(
            SpecViolation(f"{path}.early_stopping".lstrip("."), _EARLY_STOPPING_MESSAGE)
        )
    for segment, child in _children(value):
        _walk_early_stopping(child, path + segment, violations, depth + 1)


def _offenders(value: Any, reinflated: bool) -> list[Any]:
    """The values in this subtree that dumping coerces beyond recovery.

    Returning the objects rather than a flag lets `_walk` tell "this node is
    itself the offender" from "the loss is somewhere below me", which decides
    whether to report here or keep descending.
    """
    coerced: list[Any] = []

    def record(obj: Any) -> Any:
        coerced.append(obj)
        try:
            # Serialize as the real dump would, so that pydantic keeps walking
            # into a coerced value (e.g. a registry dict) and reports what is
            # nested inside it too.
            return serialize_fallback(obj)
        except Exception:
            # callable_name raises on callables with no __code__ (a partial or
            # callable object); the object is recorded, so it is still caught.
            return None

    try:
        if isinstance(value, BaseModel):
            args = {**MODEL_DUMP_ARGS, "fallback": record}
            if isinstance(value, FlowTask):
                # Owned by _walk_early_stopping; including it here would report
                # the same stopper twice.
                args["exclude"] = {"early_stopping"}
            value.model_dump(**args)
        else:
            to_jsonable_python(value, fallback=record)
        refused = False
    except Exception:
        # Pydantic would not serialize this at all (a cycle, undecodable bytes,
        # excessive depth), so something here is non-portable even if nothing
        # reached the fallback first.
        refused = True
    offenders = [
        obj
        for obj in coerced
        if not survives_round_trip(obj)
        and not (reinflated and serializes_to_registry_dict(obj))
    ]
    if refused and not offenders:
        # Attribute to a marker rather than to `value`, so the walk still
        # descends to whichever leaf actually caused the refusal.
        return [_REFUSED]
    return offenders


def _children(value: Any) -> list[tuple[str, Any]]:
    """The addressable sub-values of a node, with the path segment for each."""
    if isinstance(value, BaseModel):
        # model_fields_set mirrors the dump's exclude_unset: an unset field is
        # not serialized, so it cannot carry a value across the boundary.
        names = value.model_fields_set
        if isinstance(value, FlowTask):
            # _walk_early_stopping owns this field; descending would report a
            # live stopper a second time.
            names = names - {"early_stopping"}
        return [(f".{name}", getattr(value, name)) for name in names]
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


def _walk(
    value: Any,
    path: str,
    violations: list[SpecViolation],
    reinflated: bool = False,
    seen: frozenset[int] = frozenset(),
    depth: int = 0,
) -> None:
    if depth > _MAX_DEPTH:
        violations.append(SpecViolation(path.lstrip("."), _VALUE_MESSAGE))
        return
    offenders = _offenders(value, reinflated)
    if not offenders:
        return
    if id(value) in seen:
        # A cycle cannot be serialized at all; report here rather than recurse.
        violations.append(SpecViolation(path.lstrip("."), _VALUE_MESSAGE))
        return
    if isinstance(value, Mapping) and any(not isinstance(key, str) for key in value):
        # Keys are not children, and a non-string key is coerced to text.
        violations.append(SpecViolation(path.lstrip("."), _VALUE_MESSAGE))
        return
    children = _children(value)
    if not children or any(offender is value for offender in offenders):
        # Either there is nowhere further to look, or this node is itself one of
        # the values that failed to serialize -- which a container can be even
        # when every child of it is portable (a `range`, a `memoryview`, a
        # custom Sequence or Mapping).
        violations.append(SpecViolation(path.lstrip("."), _message(value)))
        return
    for segment, child in children:
        # Each child is judged in its own context: a value is portable under a
        # re-inflated field even though its parent, dumped as a whole, is not.
        _walk(
            child,
            path + segment,
            violations,
            reinflated or segment.lstrip(".") in _REINFLATED_FIELDS,
            seen | {id(value)},
            depth + 1,
        )
