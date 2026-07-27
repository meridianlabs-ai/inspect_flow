# Portable-spec validation

## Problem

An in-memory `FlowSpec` may legally contain live Inspect objects — an
instantiated `Task`, `Model`, `Scorer`, `Solver`, `Agent`, or `Scanner` — for
in-process execution. Those objects cannot cross a YAML/JSON boundary and be
recreated in another Python process. Flow checks this in venv execution, where
the spec is serialized with
[write_config_file](../src/inspect_flow/_config/write.py) and re-loaded in a
child process, but the check was a private launcher function
(`_check_spec_for_venv`) that:

- failed fast with a single `ValueError`, without identifying the field;
- enumerated a handful of locations and so missed live `Model`s in
  `FlowTask.model_roles`, live `Scorer`s inside scorer *sequences*, the
  `defaults.*` templates, non-reconstructable factory callables, store
  filters, and live objects buried in `args`/`metadata`; and
- was unavailable to remote orchestrators, which need the same validation
  before uploading a job and otherwise must copy the private routine.

## Ground truth

A spec is portable if it survives the boundary the child process actually
crosses:

```python
FlowSpec.model_validate(yaml.safe_load(config_to_yaml(spec)))
```

Serializing is only half of it. Two kinds of value fail to come back:

- **Anything reduced to text.** [_serialize_fallback](../src/inspect_flow/_util/pydantic_util.py)
  turns an unknown object into its `repr`, which reloads as a string.
- **Anything reduced to a registry dict.** A live registered `Scorer`, `Solver`,
  `Agent`, or `Model` serializes to `{type, name, params}`. That is *not* a
  round trip: in a structural position the child's `extra="forbid"` validation
  rejects it outright, and in a free-form container it reloads as a plain
  `dict` rather than the object.

The one thing that does survive is a callable the loader can name again —
a registry object, or a module-level function that `callable_name` renders as
`<file>@<name>`. Lambdas, `functools.partial`, nested functions, classes, and
callable objects cannot be named again (some crash `callable_name` outright).

[`survives_round_trip`](../src/inspect_flow/_util/pydantic_util.py) encodes
exactly this, and lives beside `_serialize_fallback` so the serializer and the
validator cannot drift apart.

## Design

[_config/portable.py](../src/inspect_flow/_config/portable.py) exposes the
check as a public API, exported from `inspect_flow.api`:

```python
@dataclass
class SpecViolation:
    path: str      # e.g. "tasks[2].model_roles['grader']"
    message: str   # what is wrong and the portable alternative

class SpecNotPortableError(ValueError):
    violations: list[SpecViolation]
    hint: str | None  # optional extra line appended to str()

def validate_portable_spec(spec: FlowSpec) -> None: ...
```

The implementation is a generic walk rather than a list of places to look:

- `_lossy(value)` dumps a subtree through Pydantic and asks whether any value
  that reached the fallback fails `survives_round_trip`.
- `_children(value)` yields the addressable sub-values of a node — set fields
  of a `BaseModel`, mapping items, sequence items — with the path segment for
  each.
- `_walk` prunes any subtree that dumps cleanly, descends into the rest, and
  reports a violation at the deepest node that nothing below it accounts for.

Every field is therefore covered, including `includes`, free-form containers
(`args`, `extra_args`, `model_args`, `metadata`, `flow_metadata`,
`FlowFactory.args`, scanner params), and any field added in future. The
direction of failure is what matters: an enumeration of locations fails *open*
— a location nobody listed is silently treated as portable — whereas the walk
fails *closed*, at worst reporting a coarser path than necessary.

Violation messages are chosen from the offending value's **registry type**,
not `isinstance`: `Scorer`, `Solver`, and `Agent` are runtime-checkable
Protocols that any callable satisfies structurally, so `isinstance` would
label a lambda a `Scorer`.

Messages are neutral, naming the object found and the portable alternative.
Callers with an extra escape hatch attach it via `hint`: venv execution
re-raises with the "run using 'inproc'" advice, while a remote orchestrator
reads `violations` and formats its own message. Subclassing `ValueError` keeps
existing callers working.

The function validates only portability. It does not expand or resolve the
spec, install dependencies, or launch anything.

One limitation: a value whose type Pydantic natively coerces on dump (e.g. a
`datetime` becoming an ISO string) is reported as portable, since it reloads
as the coerced type rather than being lost.

## Tests

[tests/test_portable.py](../tests/test_portable.py) asserts behaviour by field
path, and pins the design against the real boundary rather than against a
model of it:

- `test_validated_spec_survives_the_real_boundary` dumps and reloads a
  fully-populated valid spec and requires the result to match — the contract,
  asserted against the code path the child runs.
- `test_rejected_specs_do_not_survive_the_real_boundary` requires each
  rejected spec to genuinely fail to come back, so a validator that flagged a
  portable value would fail.
- `test_completeness_against_the_dump` requires every lossily-coerced leaf in
  a maximally-broken spec to be reported.

An earlier design also carried a snapshot test over spec field names, needed
because an enumeration cannot discover fields on its own. The walk makes it
unnecessary.
