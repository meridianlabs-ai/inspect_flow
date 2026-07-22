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
- missed live `Model`s in `FlowTask.model_roles`, live `Scorer`s inside scorer
  *sequences*, the `defaults.task` / `defaults.task_prefix` templates, and live
  `early_stopping` callbacks; and
- was unavailable to remote orchestrators, which need the same validation
  before uploading a job and otherwise must copy the private routine.

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

`validate_portable_spec` walks the whole spec, collects **all** violations,
and raises one `SpecNotPortableError`. Messages are neutral — they name the
live object type found and the portable alternative (`FlowModel`, registry
name, scanner spec reference). Callers with an extra escape hatch attach it
via `hint`: venv execution re-raises with the "run using 'inproc'" advice,
while a remote orchestrator can read `violations` and format its own message.
Subclassing `ValueError` keeps existing callers working.

The function validates only serializability. It does not expand or resolve
the spec, install dependencies, or launch anything. Factory callables remain
allowed: they serialize via registry name or `file@attr` reference.

## Coverage

One reusable task checker applied to every `FlowTask` at `tasks[i]`,
`defaults.task`, and `defaults.task_prefix[key]`:

- `model` and `model_roles[key]`: live `Model`;
- `scorer` / `scorer[i]`: live `Scorer` (scalar and sequence);
- `solver` / `solver[i]`: live `Solver`/`Agent` (scalar and sequence);
- `early_stopping`: any set value (`EarlyStopping` is a live-callback
  protocol with no registry/string form);
- `factory` (on the task and on any `FlowModel`/`FlowScorer`/`FlowSolver`/
  `FlowAgent` reached above): callables that cannot be recreated from the
  generated reference — lambdas, partials, nested functions, and callable
  objects. Registry objects and module-level functions are accepted.

The same `factory` check also covers the other factory-bearing defaults —
`defaults.model` / `defaults.solver` / `defaults.agent` and their `*_prefix`
mappings — so a non-reconstructable factory is rejected wherever it sits, not
only after defaults are merged into a task.

Spec-level checks:

- `tasks[i]`: instantiated `Task` objects;
- `options.scanner.scanners[...]`: entries that are not serializable scanner
  spec references;
- `options.scanner.model` and `options.scanner.model_roles[key]`: live
  `Model`;
- `store.filter` (scalar and sequence): non-reconstructable filter callables,
  by the same rule as factories.

Known limitations: specs pulled in via `includes` are not descended into
(validate the resolved spec, after includes are merged), and `args` /
`extra_args` mappings are not inspected — a live object buried in constructor
args serializes as a lossy `repr` string rather than being rejected.

Two tests guard against future drift. A snapshot test on the field names of
the spec types (`FlowSpec`, `FlowTask`, `FlowDefaults`, `FlowOptions`, the
`Flow*` wrappers, and `FlowStoreConfig`) fails when a field is added, until the
author either extends `validate_portable_spec` (live-capable field) or updates
the snapshot (plain data). A completeness oracle dumps a fully-populated spec
through Pydantic's own traversal and asserts every value that serializes
lossily is reported by the validator — so a lossy value in a covered field the
validator misses fails the test. Full annotation introspection was considered
and rejected as too fragile against inspect-ai type refactors.
