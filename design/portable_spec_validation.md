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

- **Anything reduced to text.** [serialize_fallback](../src/inspect_flow/_util/pydantic_util.py)
  turns an unknown object into its `repr`, which reloads as a string.
- **A registry dict outside a re-inflated field.** A live registered `Scorer`,
  `Solver`, `Agent`, or `Model` serializes to `{type, name, params}`. Whether
  that round-trips depends on where it sits. The runner passes `args`,
  `model_args`, and `extra_args` through `registry_kwargs`, which turns the
  dict back into the object — so a live object *is* portable there (as long as
  its own registry params are), and `tests/local_eval/flow/local_eval_flow.py`
  relies on it. Anywhere else it is not: a structural position (`tasks`,
  `model`, `scorer`, `solver`, `model_roles`) fails the child's
  `extra="forbid"` validation outright, and `metadata`/`flow_metadata` are
  handed to the task raw, so the dict stays a dict.

`early_stopping` is a third case, and the only rule the dump cannot see. The
field holds a live-callback protocol with no registry or string form, so no
value survives — including a dataclass or `BaseModel` implementation, which
serializes cleanly and reloads as a plain dict, silently losing the protocol.
It gets its own small pass over the spec.

The one thing that does survive is a callable the loader can name again —
a registry object, or a module-level function that `callable_name` renders as
`<file>@<name>`. Lambdas, `functools.partial`, nested functions, classes, and
callable objects cannot be named again (some crash `callable_name` outright).

[`survives_round_trip`](../src/inspect_flow/_util/pydantic_util.py) encodes
exactly this, and lives beside `serialize_fallback` so the serializer and the
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

- `_offenders(value, reinflated)` dumps a subtree through Pydantic and returns
  the values that reached the fallback and fail `survives_round_trip` —
  allowing registry dicts when the subtree sits under a re-inflated field.
- `_children(value)` yields the addressable sub-values of a node — set fields
  of a `BaseModel`, mapping items, sequence items — with the path segment for
  each.
- `_walk` prunes any subtree that dumps cleanly and descends into the rest,
  reporting when there is nowhere further to look **or** when the node is
  itself among the offenders. That second test is what makes the two cases
  distinguishable: a container can be the offending value even though each of
  its children is portable (a `range`, a `memoryview`, a custom `Sequence`),
  while a `FlowTask` whose only offender sits under a re-inflated `args` must
  stay silent. Each child is judged in *its own* context.
- `_walk_early_stopping` is a separate structural pass for the one rule the
  dump cannot see.

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

Two limitations. A value whose type Pydantic natively coerces on dump (e.g. a
`datetime` becoming an ISO string) is reported as portable, since it reloads
as the coerced type rather than being lost. And a live registered object in
scanner `params` is rejected even though scout would re-inflate it: that only
holds when *every* scanner entry is a spec reference, so the stricter answer
is the safe one for an unusual case.

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
