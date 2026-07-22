# Public portable-spec validation

## Status

Approved design for "Suggested PR 1" in
[hawk_upstream_suggestions.md](hawk_upstream_suggestions.md). The intent is to
make what Flow already does public and fix small coverage gaps — not to
re-engineer validation.

## Context

Flow only validates spec portability in venv execution, where the spec is
serialized to YAML and re-loaded in a child process. The private
`_check_spec_for_venv` in `_launcher/venv.py` performs that check, failing fast
with a single `ValueError`. Remote orchestrators (METR Hawk) need the same
validation before uploading a job, and currently copy the private routine.

Known coverage gaps in the private check:

- live `Model` values in `FlowTask.model_roles`;
- live `Scorer` instances inside a scorer *sequence* (only the scalar form is
  checked);
- the `defaults.task` and `defaults.task_prefix` templates (full `FlowTask`s
  that are never walked); and
- live `EarlyStopping` callbacks in `FlowTask.early_stopping` (a Protocol with
  no registry/string form, so any set value is non-portable).

Callable factories (`factory` fields, `FlowFactory`) remain allowed: they
serialize via registry name or `file@attr` and are recreated in the child.

## Public API

New module `_config/portable.py`, exported from `inspect_flow.api`:

```python
@dataclass
class SpecViolation:
    path: str      # e.g. "tasks[2].model_roles['grader']"
    message: str   # neutral: what is wrong and the portable fix

class SpecNotPortableError(ValueError):
    violations: list[SpecViolation]
    hint: str | None  # optional extra line appended to str()

def validate_portable_spec(spec: FlowSpec) -> None:
    """Raises SpecNotPortableError if the spec cannot be serialized and
    recreated in another Python process. Does not expand, resolve, install,
    or launch anything."""
```

Behavior:

- Walks the whole spec and collects **all** violations before raising one
  `SpecNotPortableError`.
- Messages are neutral (no "run using 'inproc'" advice); they name the live
  object type found and the portable alternative (`FlowModel`, registry name,
  scanner spec reference, etc.).
- `str(error)` is a header plus one `path: message` line per violation, plus
  `hint` when set.
- Subclasses `ValueError` so existing callers catching `ValueError` keep
  working.

## Coverage

One reusable task checker applied to every `FlowTask` found at `tasks[i]`,
`defaults.task`, and `defaults.task_prefix[key]`:

- `model`: live `Model`;
- `model_roles[key]`: live `Model` values;
- `scorer` / `scorer[i]`: live `Scorer` (scalar and sequence);
- `solver` / `solver[i]`: live `Solver`/`Agent` (scalar and sequence);
- `early_stopping`: any set value.

Spec-level checks (ported from the private function):

- `tasks[i]`: instantiated `Task` objects;
- `options.scanner.scanners[...]`: entries that are not serializable scanner
  spec references;
- `options.scanner.model` and `options.scanner.model_roles[key]`: live
  `Model`.

## Venv integration

`_venv_spawn` calls `validate_portable_spec(spec)` and re-raises
`SpecNotPortableError` with `hint` set to the existing "or run using 'inproc'
execution type" advice. `_check_spec_for_venv` is deleted. Hawk calls the
public function directly, reads `violations`, and formats its own message.

## Future-field guard

A snapshot test asserts the exact field-name sets of `FlowSpec`, `FlowTask`,
`FlowDefaults`, and `FlowOptions` against hardcoded lists. Adding any new field
fails the test with a message instructing the author to either extend
`validate_portable_spec` (if the field can hold live objects) or add the name
to the snapshot. This deliberately trades precision for simplicity; full
annotation introspection was considered and rejected as too fiddly for this
PR.

## Tests

- Migrate existing `_check_spec_for_venv` tests to `validate_portable_spec`.
- New cases: each closed gap (model_roles, scorer sequences, defaults
  templates, early_stopping); multiple violations aggregated with correct
  paths; valid specs (including factories and scanner spec references) pass.
- Venv-mode test that the raised error includes the inproc hint.
- The field-name snapshot test.
