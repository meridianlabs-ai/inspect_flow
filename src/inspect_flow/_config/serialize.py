import math
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from inspect_ai._util.registry import registry_value
from pydantic import ValidationError

from inspect_flow._types.flow_types import FlowSpec, not_given
from inspect_flow._util.pydantic_util import (
    callable_name,
    is_nameable_callable,
    model_dump,
    serializes_to_registry_dict,
)

_NOT_GIVEN_DATA = not_given.model_dump(mode="json")


def dump_spec(spec: FlowSpec) -> dict[str, Any]:
    """Dump a flow spec to its canonical wire representation.

    The returned dict is JSON-compatible and stable: re-dumping a reloaded spec
    reproduces it exactly, i.e.
    `dump_spec(load_spec_data(dump_spec(spec))) == dump_spec(spec)`. Fields that
    are unset — or explicitly set to their default value — are omitted, so
    effective values always survive a round trip but `model_fields_set`
    membership does not. Explicit `None` is preserved, and Flow's `NotGiven`
    sentinel never appears. Live values normalize to references (a
    registered callable to its registry name, a registry object such as a tool
    in agent args to its reference dict), so a reloaded spec is wire-equivalent
    to, but not necessarily object-equal to, the original. The runner resolves
    a name back to a callable only in `factory` fields and `store.filter`; in
    any other position (e.g. factory `args`) the name reloads as a plain
    string — `validate_portable_spec` flags these before dumping. Typed values
    are normalized through validation, so a coercible value assigned without
    validation (e.g. a numeric string in a float field) dumps in canonical form.

    Values in untyped fields (e.g. `flow_metadata`, `model_args`) should be
    JSON-native; anything else follows pydantic's JSON coercion (a tuple becomes
    a list, a `datetime` a string, a set a list in unspecified order) and may
    not round-trip. In fields that skip
    validation (e.g. `early_stopping`), serializable live objects carry
    one-way: they reload as plain data. Arguments captured in a registered
    object's params are encoded by inspect-ai at construction time
    (non-serializable values are already stringified before Flow sees them).
    Whether a reference resolves in the target process — installed packages,
    shipped files — is a separate concern; gate portable use with
    `validate_portable_spec` before dumping. YAML/JSON rendering is left to the
    caller.

    Args:
        spec: The flow spec to dump.

    Returns:
        A JSON-compatible dict representation of the spec.

    Raises:
        ValueError: If the spec cannot be reconstructed from its dump: a live
            Inspect object in a typed field, an unregistered callable that
            pydantic cannot serialize as data such as a plain function or
            lambda (a callable *object* with serializable fields in an untyped
            position instead follows the data-coercion rule above and reloads
            as plain data), a non-finite float, or a `NotGiven` sentinel in an
            untyped mapping (including a user value of that exact shape, which
            is indistinguishable on the wire).
    """
    # JSON-mode serialization silently degrades non-finite floats (kept in
    # FlowBase fields, nulled in untyped mappings, dropped entirely by nested
    # inspect-ai models), so check the original python values first. This pass
    # sees raw user objects, so it needs the strict fallback too — the lenient
    # one assumes every callable has __code__ (builtins and partials do not)
    _reject_invalid_wire_data(
        model_dump(spec, mode="python", fallback=_wire_fallback), path=""
    )
    data = model_dump(spec, fallback=_wire_fallback)
    # return the re-dump of the re-validated spec, so the output is canonical
    # by construction: a coercible value assigned without validation (pydantic
    # does not validate on assignment) normalizes instead of leaking its
    # non-canonical form onto the wire
    verified = _verify_reloadable(data)
    # re-validation itself coerces (e.g. an unvalidated "1e999" becomes inf),
    # so check the verified values as well — symmetric with load_spec_data
    _reject_invalid_wire_data(model_dump(verified, mode="python"), path="")
    canonical = model_dump(verified, fallback=_wire_fallback)
    # invariant on the exact returned value (the earlier walks inspect
    # intermediate forms, whose serialization pydantic may change)
    _reject_invalid_wire_data(canonical, path="")
    return canonical


def load_spec_data(data: Mapping[str, Any]) -> FlowSpec:
    """Reconstruct a flow spec from its canonical wire representation.

    Inverse of `dump_spec()`. Validation is strict: unknown fields are rejected
    (except in `FlowFactory` mappings, whose API forwards unrecognized keys as
    factory arguments), as is an embedded `NotGiven` sentinel or a non-finite
    float (whether present literally or produced by coercing a string such as
    `"NaN"`). JSON and YAML parsers accept both, but they signal data that did
    not come from `dump_spec()`, and a sentinel would be misread as a user
    value.

    Args:
        data: Spec data produced by `dump_spec()`, possibly after a JSON or
            YAML round trip.

    Returns:
        The reconstructed flow spec.

    Raises:
        ValueError: If the data contains a `NotGiven` sentinel or a non-finite
            float, or fails spec validation.
    """
    _reject_invalid_wire_data(data, path="")
    spec = FlowSpec.model_validate(data, extra="forbid")
    # pydantic coerces numeric strings, so a value like "1e999" only becomes a
    # non-finite float after validation; check the validated values as well
    _reject_invalid_wire_data(model_dump(spec, mode="python"), path="")
    return spec


def _verify_reloadable(data: dict[str, Any]) -> FlowSpec:
    # A live object created by a registry factory (e.g. an @task/@solver
    # instance) serializes to a registry dict that is fine in an untyped `args`
    # mapping but does not fit a typed field like `tasks` or `solver`. Position
    # is invisible to _wire_fallback, so enforce the round-trip contract by
    # confirming the dump actually re-validates. This also covers any future
    # typed field that accepts live objects.
    try:
        return FlowSpec.model_validate(data, extra="forbid")
    except ValidationError as e:
        raise ValueError(
            "The spec cannot be reconstructed in another process: its dump does "
            "not re-validate. This usually means a typed field holds a live "
            "Inspect object (e.g. an instantiated Task, Model, Solver, Scorer, "
            "or Agent) whose serialized form does not fit that field; replace it "
            "with a Flow type or a registry/file name reference. Affected "
            f"field(s): {', '.join(_affected_fields(e))}."
        ) from e


def _affected_fields(error: ValidationError) -> list[str]:
    # pydantic's union `loc` tuples carry verbose validator tags at varying
    # depths; the reliable, readable signal is the top-level field and index.
    fields = set()
    for err in error.errors():
        loc = err["loc"]
        if not loc:
            continue
        index = next((p for p in loc if isinstance(p, int)), None)
        fields.add(f"{loc[0]}[{index}]" if index is not None else str(loc[0]))
    return sorted(fields)


def _wire_fallback(obj: Any) -> Any:
    if serializes_to_registry_dict(obj):
        return registry_value(obj)
    # only a registered callable has a reconstructable reference (its registry
    # name); an unregistered callable would encode as a file@name reference
    # that the runtime resolver, which looks up the registry, cannot rebuild
    value = registry_value(obj)
    if is_nameable_callable(value):
        return callable_name(value)
    raise ValueError(
        f"{type(obj).__name__} object cannot be represented in a portable spec "
        "dump: only registered objects reconstruct in another process. Register "
        "a factory with @task/@solver/@scorer/@agent, or use a Flow type or a "
        "registry/file name string (e.g. FlowTask, FlowModel)."
    )


def _reject_invalid_wire_data(value: Any, path: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(
            f"{path or 'spec'}: non-finite float {value} cannot be represented "
            "in standards-compliant JSON. Use a finite value."
        )
    if isinstance(value, Iterator):
        raise ValueError(
            f"{path or 'spec'}: a single-use iterator cannot be serialized "
            "deterministically (dumping consumes it). Materialize it to a list."
        )
    if isinstance(value, Mapping):
        if value == _NOT_GIVEN_DATA:
            raise ValueError(
                f"{path or 'spec'}: contains the serialized NotGiven sentinel "
                '{"type": "NOT_GIVEN"}, which would be misread as a user value.'
            )
        for key, item in value.items():
            _reject_invalid_wire_data(key, path)
            _reject_invalid_wire_data(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, (set, frozenset)):
        # sets only occur in untyped pre-serialization values (json mode
        # coerces them to lists); their members still need checking
        for item in value:
            _reject_invalid_wire_data(item, path)
    elif isinstance(value, Sequence) and not isinstance(value, str):
        for index, item in enumerate(value):
            _reject_invalid_wire_data(item, f"{path}[{index}]")
