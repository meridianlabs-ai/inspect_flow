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
  dict back into the object — so a live object *is* portable there, and
  `tests/local_eval/flow/local_eval_flow.py` relies on it. Anywhere else it is
  not: a structural position (`tasks`, `model`, `scorer`, `solver`,
  `model_roles`) fails the child's `extra="forbid"` validation outright, and
  `metadata`/`flow_metadata` are handed to the task raw, so the dict stays a
  dict. Note the object comes back rebuilt from its registry *params*, which
  inspect reduces to JSON placeholders at registration — so a non-JSON
  constructor argument is replaced by a placeholder string rather than being
  restored. No dump-based check can see that, since the substitution happens
  before serialization.

`early_stopping` is a third case, and the only rule the dump cannot see. The
field holds a live-callback protocol with no registry or string form, so no
value survives — including a dataclass or `BaseModel` implementation, which
serializes cleanly and reloads as a plain dict, silently losing the protocol.
It gets its own small pass over the spec.

The one callable that survives is a **registered** object. `callable_name`
renders a registry object as its registry name and anything else as
`<file>@<name>`, but every resolver of that second form — inspect's task /
model / scorer / solver / agent loader, and
[_types/log_filter.py](../src/inspect_flow/_types/log_filter.py) for store
filters — imports the file and then does a *registry lookup*. So an
undecorated function is no more portable than a lambda; it merely fails later,
in the child, with `Task named '...' not found`. Lambdas,
`functools.partial`, nested functions, classes, and callable objects fail the
same way (some crash `callable_name` outright).

[`survives_round_trip`](../src/inspect_flow/_util/pydantic_util.py) encodes
exactly this, and lives beside `serialize_fallback` so the serializer and the
validator cannot drift apart.

## Design

[_config/portable.py](../src/inspect_flow/_config/portable.py) exposes the
check as a public API, exported from `inspect_flow.api`:

```python
@dataclass
class SpecViolation:
    path: str  # e.g. "tasks[2].model_roles['grader']"
    message: str  # what is wrong and the portable alternative


class SpecNotPortableError(ValueError):
    violations: list[SpecViolation]
    hint: str | None  # optional extra line appended to str()


def validate_portable_spec(spec: FlowSpec) -> None: ...
```

The implementation is a generic walk rather than a list of places to look:

- `_offenders(value, reinflated=…, resolving=…)` dumps a subtree through
  Pydantic and returns the values that reached the fallback and cannot be
  reloaded — allowing registry dicts under a re-inflated field, and named
  callables in a field the runner resolves names in.
- `_children(value)` yields the addressable sub-values of a node — set fields
  of a `BaseModel`, mapping items, sequence items — with the path segment for
  each.
- `_walk` prunes any subtree that dumps cleanly and descends into the rest.
  Its guards run fatal-and-cheap first (excessive depth), then the prune, then
  the three cases where descending cannot help — a cycle, a mapping key that
  cannot round-trip, and a node with no children or which is itself among the
  offenders — then descent, then a post-descent fallback for a subtree pydantic
  refused outright that no child accounted for. The self-offender and refusal
  cases are what make the two situations distinguishable: a container can be
  the offending value even though each of its children is portable (a `range`,
  a `memoryview`, a `bytearray` of undecodable bytes), while a `FlowTask` whose
  only offender sits under a re-inflated `args` must stay silent.
- Each child is judged in its own context, and the two flags spread
  differently. `registry_kwargs` recurses to any depth, so `reinflated` sticks
  for a whole subtree; a name lookup applies only to the value in the field
  itself, so `resolving` is replaced on entering a new field and inherited only
  through container indexing. Otherwise `FlowFactory.args` would inherit the
  excuse from the `factory` field it hangs off.
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

Known limitations:

- A value whose type Pydantic natively coerces on dump (e.g. a `datetime`
  becoming an ISO string) is reported as portable, since it reloads as the
  coerced type rather than being lost.
- A registered object's *name* must also be resolvable in the child. Inspect
  qualifies names of objects defined in an installed package
  (`local_eval/noop2`), which the child imports; a bare name from a loose
  module (`a_task`) relies on that module already being imported, and fails in
  a fresh process with `No tasks found`. The validator cannot tell the two
  apart reliably, so it does not try — prefer factories from packaged code.
  Emitting `<file>@<name>` instead would fix venv but not a remote runner,
  where the submitting machine's paths do not exist.
- A live registered object in scanner `params` is rejected even though scout
  would re-inflate it: that only holds when *every* scanner entry is a spec
  reference, so the stricter answer is the safe one for an unusual case.
- `_offenders` dumps each subtree in isolation, which cannot apply
  `exclude_unset`/`exclude_defaults` the way the boundary does. A non-portable
  value in a field the boundary *excludes* can therefore be reported against
  its nearest childless ancestor — a false positive, reachable only via a
  pydantic model with a non-portable default inside a free-form container.
- Conversely, what a `@computed_field` or custom `@model_serializer` emits is
  invisible to `_children`, so a non-portable value there is missed when the
  model has any set field. No type reachable from a `FlowSpec` in inspect-ai or
  inspect-scout has either, so this needs a user-defined model in a free-form
  container.

The last two share one cause: `_offenders` and `_children` are separate
traversals, so they can disagree about what the boundary actually serializes.
See "Attribute unexplained offenders to their node" below for why closing them
is not as cheap as it looks.

## Rejected alternatives

Each of these has been proposed by a reviewer, tried, and rejected for a
specific reason. Recorded so the reasoning is not relitigated.

**Enumerate the locations to check** — the original design, and what
`_check_spec_for_venv` did. Rejected because an allow-list of locations fails
*open*: a field nobody listed is silently treated as portable. Five review
rounds each found another missed location before the walk replaced it. If you
are tempted to add a location-specific check, add it to the walk's inputs
instead.

**Introspect field annotations** to find live-capable fields. Rejected as
fragile: it must unwrap unions, sequences, mappings, `SkipValidation`, and
generics like `FlowFactory[Task]` (where `Task` appears but is allowed), and it
breaks whenever inspect-ai refactors a type — which this repo tracks closely.

**Attribute unexplained offenders to their node**, generalizing the refusal
branch so that a `@computed_field` or custom `@model_serializer` emitting a
non-portable value is caught. Tried twice, in two forms:

- *Naively*, reporting whenever no child reported. This reintroduces the
  original CI break: a `FlowTask` whose only offender sits under a re-inflated
  `args` reports at `tasks[0]`, rejecting
  `tests/local_eval/flow/local_eval_flow.py`.
- *With recorded-object identity*, so that an offender a child's dump saw is
  treated as excused and only an unreachable one is reported. This still fails,
  because a node's dump cannot apply `exclude_unset`/`exclude_defaults` to a
  nested model: the parent sees values the boundary drops, so making it
  authoritative rejects specs that work. Reverting to it fails
  `test_refusal_is_not_blamed_on_a_node_whose_dump_overreached` and
  `test_live_inspect_objects_rejected`.

The trade is a rare false negative (needs a user-defined model with a computed
field in a free-form container) against a rare false positive (rejecting a spec
that runs). False positives are worse here — two of them broke CI — so the
refusal branch stays narrow. A complete fix needs one dump, at the root, with
the boundary's own flags, feeding both the offender set and the traversal; that
is a larger change than this validator and belongs with a canonical
serialization API.

**Emit `<file>@<name>` for registry objects** so a bare registry name always
resolves in the child. Rejected because it fixes venv execution and breaks
remote: a path from the submitting machine does not exist in a runner pod, which
is the case this API exists for. The portable answer is a package-qualified name
plus the dependency, which already works.

**Reject bare (unqualified) registry names** in `factory` fields. Rejected as a
policy call with false-positive risk: a bare name does resolve when its module
is imported, so this would reject working specs. Documented as a limitation
instead.

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
- `test_maximally_broken_spec_reports_every_path` snapshots one spec that
  breaks every rule at once, so a change in how paths are attributed shows up
  in one place. It is not self-discovering: a new live-capable field has to be
  added to it by hand.

An earlier design also carried a snapshot test over spec field names, needed
because an enumeration cannot discover fields on its own. The walk makes it
unnecessary.
