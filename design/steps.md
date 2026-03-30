## Problem

After `flow run` produces eval logs, users need to QA and promote them through diverse, org-specific workflows. Examples: tag logs as QA'd, validate that scores meet thresholds, copy golden logs to a production S3 bucket. No single workflow fits all teams, so we need composable atomic steps.

## Atomic Steps

A step is an operation that modifies log files and returns the set of modified logs. The return value becomes the input for subsequent steps, enabling natural chaining.

Three operations that users compose into workflows:

| Step | Purpose | Output |
|---|---|---|
| `tag` | Add/remove tags on log files | Modified source logs |
| `metadata` | Set/delete metadata fields on log files | Modified source logs |
| `copy` | Copy log files to another location | New destination logs |

> Filtering (selecting a subset of logs) is not a step — users use list comprehensions or `store.get_logs(filter=...)` from [PR #552](https://github.com/meridianlabs-ai/inspect_flow/pull/552) instead.

> Validation (asserting conditions on logs) is not a step — it doesn't modify logs and has no meaningful "set of modified logs" to pass forward. Use `validate()` as a standalone function call within a step or script.

## Dependencies

The `tag` and `metadata` steps depend on Inspect AI's [log editing API](https://inspect.aisi.org.uk/reference/inspect_ai.log.html#log-editing) (`edit_eval_log`, `TagsEdit`, `MetadataEdit`, `ProvenanceData`).

`validate` and user-defined filtering use `LogFilter = Callable[[EvalLog], bool]` and the `@log_filter` registry from [store_filters.md](store_filters.md).

## Execution Model

Steps have two modes of operation, determined by the input type:

### Standalone mode (paths)

When called with file paths (`str | Sequence[str]`), each step reads headers from disk, operates, and writes back immediately. This is the mode used by the CLI and for one-off Python API calls.

```python
# Standalone: reads, modifies, writes immediately
tag("./logs/2026-03-11/", tags_add=["reviewed"])
```

### Composition mode (in-memory EvalLog headers)

When called with `EvalLog` objects (`EvalLog | Sequence[EvalLog]`), steps operate in-memory and return modified `EvalLog` objects without writing to disk. This enables efficient chaining — headers are read once and passed through the pipeline.

```python
# Composition: in-memory, no disk I/O per step
logs = [log for log in logs if my_condition(log)]   # list comprehension for filtering
logs = tag(logs, tags_add=["golden"])               # returns list[EvalLog], modified in-memory
logs = copy(logs, dest="s3://my-org/prod/golden")   # returns destination logs
```

The `@step` decorator manages the boundary: it reads headers at entry, passes `list[EvalLog]` to the function, and writes back modified logs at exit. This means:

- **Read once**: all headers are read at the start of the step
- **Write once**: all modified logs are written back at the end
- **Natural rollback for tag/metadata**: if any operation raises before the step completes, nothing has been written to disk

### How `copy` works in composition mode

When `copy` receives `EvalLog` object headers (with in-memory tag/metadata edits), it:

1. Reads the full original log from `log.location` (including samples)
2. Overlays the in-memory modified header onto the full log
3. Writes the combined result to the destination

The destination gets the final state (with all pending edits) in a single write. Originals are not modified by `copy`. The return value is the set of new destination logs — subsequent steps operate on those.

#### How `copy` works in the `@step` decorator

```
# Inside @step:
# 1. tag() modifies EvalLog header in-memory (adds "golden" tag)
# 2. copy() reads full original from log.location,
#    overlays the modified header (with "golden" tag),
#    writes to destination — originals NOT modified yet
# 3. @step write-back: reads full original again, overlays modified header,
#    writes back to original location
```

**Open question:** For logs that are both modified (tag/metadata) and copied, the full log is read twice — once by `copy` (to write to destination) and once by `@step` write-back (to update the original). For S3, this doubles the I/O cost. We might want to skip writing back to originals, although that might be unexpected behavior.

**Rollback**: If `copy` fails mid-batch, originals are untouched (no headers written yet). If `@step` write-back fails after `copy` succeeded, the destination has the correct content — only the originals are missing the edits, and the user can re-run.

### How `@step` manages the lifecycle

```
1. CLI/caller provides paths
2. @step reads all headers: read_eval_log(path, header_only=True) for each
3. @step calls the function body with list[EvalLog]
4. Inside the function:
   - validate and list comprehensions operate on in-memory headers (no I/O)
   - tag/metadata call edit_eval_log() in-memory, return modified EvalLogs
   - copy reads full log from log.location, overlays modified header, writes to destination
5. Function returns list[EvalLog] of modified logs
6. @step writes back all modified logs to their original locations
7. If the function raises at any point, no tag/metadata edits are persisted to originals
```

### Overloaded signatures

Each step function is overloaded to accept both paths and EvalLog objects:

```python
@overload
def tag(logs: str | Sequence[str], *, tags_add: ...) -> list[str]: ...
@overload
def tag(logs: EvalLog | Sequence[EvalLog], *, tags_add: ...) -> list[EvalLog]: ...
```

The return type matches the input type: paths in → paths out, EvalLog in → EvalLog out.

## Log Resolution

Steps accept log paths or EvalLog objects, not store queries. Users who want to pull from the store do so explicitly:

```python
store = store_get()
paths = store.get_logs(filter=my_filter)
tag(paths, tags_add=["reviewed"])
```

## Python API

### Provenance

All mutating steps (`tag`, `metadata`) require provenance. The Python API offers two ways to provide it:

1. **Convenience parameters** (`author`, `reason`): For simple cases. If omitted, `author` defaults to git `user.name <user.email>` (falling back to OS username), `timestamp` is always now.
2. **Full `ProvenanceData` object**: For complete control. When provided, convenience parameters are ignored.

```python
from inspect_ai.log import ProvenanceData

def default_provenance(
    author: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ProvenanceData:
    """Create provenance with sensible defaults.

    `author` defaults to git `user.name <user.email>`, falling back to
    the OS username. `timestamp` is always now.
    """
    ...
```

### `tag`

```python
@overload
def tag(
    logs: str | Sequence[str],
    *,
    tags_add: list[str] | None = None,
    tags_remove: list[str] | None = None,
    provenance: ProvenanceData | None = None,
    author: str | None = None,
    reason: str | None = None,
    recursive: bool = True,
    dry_run: bool = False,
) -> list[str]: ...

@overload
def tag(
    logs: EvalLog | Sequence[EvalLog],
    *,
    tags_add: list[str] | None = None,
    tags_remove: list[str] | None = None,
    provenance: ProvenanceData | None = None,
    author: str | None = None,
    reason: str | None = None,
) -> list[EvalLog]: ...

def tag(logs, *, tags_add=None, tags_remove=None, provenance=None,
        author=None, reason=None, recursive=True, dry_run=False):
    """Add or remove tags on eval logs.

    Under the hood: applies TagsEdit via edit_eval_log.

    In standalone mode (paths): reads each log, applies edit, writes back.
    In composition mode (EvalLog objects): applies edit in-memory, returns
    modified EvalLog objects without writing to disk.

    When `provenance` is None, one is auto-generated from `author`/`reason`
    (with defaults). If `provenance` is provided, `author`/`reason` are ignored.

    Args:
        logs: Log file(s), directory(ies), or EvalLog object(s).
        tags_add: Tags to add.
        tags_remove: Tags to remove.
        provenance: Full provenance object. Overrides author/reason.
        author: Provenance author. Defaults to git user.
        reason: Provenance reason.
        recursive: Recurse into directories (standalone mode only).
        dry_run: Preview changes without writing (standalone mode only).
            Validates that all logs can be read and edits can be applied.

    Returns:
        Paths of modified logs (standalone) or modified EvalLog objects (composition).
    """
```

### `metadata`

```python
@overload
def metadata(
    logs: str | Sequence[str],
    *,
    metadata_set: dict[str, Any] | None = None,
    metadata_remove: list[str] | None = None,
    provenance: ProvenanceData | None = None,
    author: str | None = None,
    reason: str | None = None,
    recursive: bool = True,
    dry_run: bool = False,
) -> list[str]: ...

@overload
def metadata(
    logs: EvalLog | Sequence[EvalLog],
    *,
    metadata_set: dict[str, Any] | None = None,
    metadata_remove: list[str] | None = None,
    provenance: ProvenanceData | None = None,
    author: str | None = None,
    reason: str | None = None,
) -> list[EvalLog]: ...

def metadata(logs, *, metadata_set=None, metadata_remove=None, provenance=None,
             author=None, reason=None, recursive=True, dry_run=False):
    """Set or delete metadata fields on eval logs.

    Under the hood: applies MetadataEdit via edit_eval_log.

    In standalone mode (paths): reads each log, applies edit, writes back.
    In composition mode (EvalLog objects): applies edit in-memory, returns
    modified EvalLog objects without writing to disk.

    Args:
        logs: Log file(s), directory(ies), or EvalLog object(s).
        metadata_set: Key-value pairs to set.
        metadata_remove: Keys to delete.
        provenance: Full provenance object. Overrides author/reason.
        author: Provenance author. Defaults to git user.
        reason: Provenance reason.
        recursive: Recurse into directories (standalone mode only).
        dry_run: Preview changes without writing (standalone mode only).
            Validates that all logs can be read and edits can be applied.

    Returns:
        Paths of modified logs (standalone) or modified EvalLog objects (composition).
    """
```

### `validate`

`validate` is a standalone function, not a step. It doesn't modify logs and returns a result rather than a set of logs to pass forward.

```python
@dataclass
class ValidationResult:
    """Result of a validation run."""
    passed: list[str]
    failed: list[str]

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0


class ValidationError(Exception):
    """Raised when validation fails."""
    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        n = len(result.failed)
        super().__init__(f"Validation failed: {n} log(s) did not pass")


@overload
def validate(
    logs: str | Sequence[str],
    condition: LogFilter,
    *,
    recursive: bool = True,
) -> ValidationResult: ...

@overload
def validate(
    logs: EvalLog | Sequence[EvalLog],
    condition: LogFilter,
) -> ValidationResult: ...

def validate(logs, condition, *, recursive=True):
    """Assert that all logs satisfy a condition.

    Applies the condition to each log header. If any log fails,
    raises ValidationError with a report of passed/failed paths.

    Args:
        logs: Log file(s), directory(ies), or EvalLog object(s).
        condition: A callable (EvalLog) -> bool.
        recursive: Recurse into directories (standalone mode only).

    Returns:
        ValidationResult (only reached if all pass).

    Raises:
        ValidationError: If any log fails the condition.
    """
```

### `copy`

```python
@overload
def copy(
    logs: str | Sequence[str],
    dest: str,
    *,
    recursive: bool = True,
    dry_run: bool = False,
    import_store: str | None = None,
) -> list[str]: ...

@overload
def copy(
    logs: EvalLog | Sequence[EvalLog],
    dest: str,
    *,
    dry_run: bool = False,
    import_store: str | None = None,
) -> list[EvalLog]: ...

def copy(logs, dest, *, recursive=True, dry_run=False, import_store=None):
    """Copy log files to a destination directory.

    Preserves directory structure relative to the common prefix of the
    source paths.

    In standalone mode (paths): copies files directly.
    In composition mode (EvalLog objects): reads the full original log
    from log.location, overlays the in-memory modified header, and writes
    the combined result to the destination.

    Args:
        logs: Log file(s), directory(ies), or EvalLog object(s).
        dest: Destination directory (local or S3).
        recursive: Recurse into source directories (standalone mode only).
        dry_run: Preview without copying. Validates that all source
            logs can be read and the destination is writable.
        import_store: If set, auto-import copied logs into this store.
            Use "auto" for default store. None to skip (default).

    Returns:
        Destination paths of copied logs (standalone) or destination
        EvalLog objects (composition). Subsequent steps operate on the
        destination logs, not the originals.
    """
```

### Composition Examples

#### Inline composition (no `@step`)

```python
from inspect_flow import validate, tag, copy, store_get
from inspect_ai.log import read_eval_log, write_eval_log

# Read headers once, chain in-memory
store = store_get()
paths = store.get_logs(filter=lambda log: "gpt-6" in (log.eval.model or ""))
logs = [read_eval_log(p, header_only=True) for p in paths]
validate(logs, condition=lambda log: "qa_done" in (log.eval.tags or []))
logs = tag(logs, tags_add=["golden"], reason="Promoted after QA")
# copy overlays modified headers onto full logs and writes to destination
copy(logs, dest="s3://my-org/prod/golden-logs", import_store="auto")
# Write modified headers back to originals
for log in logs:
    write_eval_log(log, log.location)
```

#### With `@step` (handles read/write automatically)

```python
from inspect_flow import step, validate, tag, copy

@step
def promote(logs: list[EvalLog], *, dest: str = "s3://my-org/prod/golden") -> list[EvalLog]:
    logs = [log for log in logs if "testing_exercise" in (log.eval.tags or [])]
    validate(logs, condition=lambda log: "auto_qa_passed" in (log.eval.tags or []))
    logs = tag(logs, tags_add=["golden"], reason="Promoted after QA")
    return copy(logs, dest=dest)
    # @step writes modified headers back to originals here

# From paths — @step reads headers and writes back on success
promote("./logs/2026-03-11/")

# From store — caller resolves paths, @step handles the rest
store = store_get()
promote(store.get_logs(filter=my_filter))
```

## CLI Interface

### Individual step commands

All steps live under `flow step`:

```
flow step tag PATH... --add qa_done --add reviewed --author "Alice" --reason "Manual QA"
flow step tag PATH... --remove draft
flow step metadata PATH... --set key=value --set score_threshold=0.9
flow step metadata PATH... --remove old_key
flow step copy PATH... --dest s3://bucket/golden --import-store auto
```

Common options across all `flow step` subcommands:
- `PATH...` — log files or directories (positional). Mutually exclusive with `--store`.
- `--store` (`-s`) — resolve logs from this store instead of PATH. Use `"auto"` for default store location. Mutually exclusive with `PATH...`.
- `--filter` — registered `@log_filter` name to pre-filter which logs are passed to the step. Works with both `PATH...` and `--store`.
- `--recursive/--no-recursive` (`-r/-R`) — recurse into directories (default: true)
- `--dry-run` — preview without making changes; validates that logs can be accessed and operations can be applied (for mutating steps: `tag`, `metadata`, `copy`)

For `tag` and `metadata`:
- `--author` — provenance author (default: git user)
- `--reason` — provenance reason
- `--timestamp` — provenance timestamp (default: now)
- `--provenance-metadata` — arbitrary key=value pairs for provenance metadata

### User-Defined Steps

Users define reusable workflows with `@step`, which are also discoverable under `flow step`:

```python
from inspect_flow import step, validate, tag, copy


def _scores_pass(log: EvalLog) -> bool:
    """Check that refusal_score == 0 and tool_errors == 0."""
    for score in log.results.scores:
        metrics = score.metrics
        if "refusal_score" in metrics and metrics["refusal_score"].value != 0:
            return False
        if "tool_errors" in metrics and metrics["tool_errors"].value != 0:
            return False
    return True


@step
def qa(logs: list[EvalLog]) -> list[EvalLog]:
    """Automated QA: validate scores and tag logs as passed or failed."""
    passed = [log for log in logs if _scores_pass(log)]
    failed = [log for log in logs if log not in passed]
    if passed:
        tag(passed, tags_add=["auto_qa_passed"], reason="Automated QA: scores passed")
    if failed:
        tag(failed, tags_add=["auto_qa_failed"], reason="Automated QA: refusal or tool error")
    return passed + failed


@step
def promote(logs: list[EvalLog], *, dest: str = "s3://my-org/prod/golden") -> list[EvalLog]:
    """Promote QA-passed logs to golden storage."""
    logs = [log for log in logs if "testing_exercise" in (log.eval.tags or [])]
    validate(logs, condition=lambda log: "auto_qa_passed" in (log.eval.tags or []))
    logs = tag(logs, tags_add=["golden"], reason="Promoted after automated QA")
    return copy(logs, dest=dest)
```

CLI invocation:

```
# Run automated QA on logs in a directory
flow step qa ./logs/2026-03-11/

# Run automated QA on logs from the store
flow step qa --store s3://my-org/flow/store --filter success_only

# Promote QA-passed logs from a directory
flow step promote ./logs/2026-03-11/ --dest s3://my-org/prod/golden

# Promote QA-passed logs from the store
flow step promote --store s3://my-org/flow/store --filter has_tag_qa_passed --dest s3://my-org/prod/golden
```

#### CLI generation from `@step` parameters

The `@step` decorator auto-generates a CLI command from the function signature:

- The first parameter accepting `list[EvalLog]` becomes the `PATH...` argument (the decorator handles path → EvalLog conversion).
- Type annotations drive click types (`str` → STRING, `int` → INT, `float` → FLOAT, `bool` → flag).
- Snake_case parameter names become --kebab-case on CLI.
- `--store` and `--filter` are auto-injected on all `@step` CLI commands as an alternative to `PATH...`. When `--store` is provided (and PATH is omitted), logs are resolved from the store. `--filter` accepts a registered `@log_filter` name to pre-filter which logs are passed to the step function.

For example, `def promote(logs, *, dest: str = "s3://...")` generates:

```
flow step promote PATH... --dest s3://...
flow step promote --store auto --filter my_filter --dest s3://...
```

`PATH...` and `--store` are mutually exclusive — provide one or the other.

## API Surface

### Public API (`_api/api.py`)

```python
# New exports
from inspect_flow import tag, metadata, validate, copy, step
from inspect_flow import ValidationResult, ValidationError
```

### CLI (`_cli/main.py`)

```python
flow.add_command(step_command)  # flow step tag|metadata|copy|<user-defined>
```

## Open Questions

### 1. Paths-only vs in-memory EvalLog composition

**Current design:** Dual-mode — steps accept both paths (standalone, immediate read/write) and EvalLog objects (composition, in-memory). `@step` manages the boundary. Gives natural rollback and read-once efficiency, but requires overloaded signatures, dirty tracking, and `@step` lifecycle management.

**Alternative:** Paths-only — steps always take paths, read/write immediately. Simpler API (one signature per step), no dirty tracking, easy to implement. But no rollback (tag writes are immediate), and redundant I/O when chaining steps on S3.

**Key constraint:** Inspect AI's `write_eval_log()` always rewrites the full file including samples — no header-only write exists. Both approaches require a full read+write per modified log. The in-memory model saves repeated header reads in multi-step pipelines but not writes.

### 2. Transactionality / Rollback

Steps are not transactional. The most important properties are:

- **Idempotency**: All steps should be safe to re-run. Tag/metadata edits are already idempotent (Inspect handles this). `copy` should support overwrite-or-skip behavior — consider a flag (e.g., `overwrite: bool`) to control whether existing files at the destination are overwritten or skipped.
- **Transparency on failure**: When a step errors mid-execution, logs should clearly report which changes were applied and which were not, so the user knows the state they're in.

### 3. Dirty tracking

`@step` needs to know which logs were modified so it only writes back changed logs. Options:

- **Snapshot + diff**: `@step` keeps a copy of original headers, compares at commit. Simple but requires deep comparison of EvalLog objects.
- **Dirty flag / set**: `tag`/`metadata` register each modified EvalLog in a side-channel set (e.g., via `contextvars`).
- **Always write all**: Write back every log that entered the function. Wasteful if only a subset was modified, but simplest to implement.

### 4. Step discovery

User-defined `@step` functions are discoverable under `flow step`. How does the CLI find registered steps? Options include a global registry, scanning a specific module (e.g., `_flow.py`), or explicit registration.

### 5. Concurrency

Two users running tag/copy on overlapping log sets on S3 simultaneously could cause conflicts. For tag/metadata writes, Inspect AI supports optimistic concurrency via `write_eval_log(if_match_etag=log.etag)` — S3 rejects the write with `WriteConflictError` if the file was modified since it was read. We should use this. For `copy`, ETags don't help since the destination is a new file (last-write-wins).

## Future Directions

### Satisfy / Completeness Check

There's a related but separate concept: "do all the logs that a spec *requires* exist and pass QA?" This is a different kind of validation — it checks completeness against a spec rather than a condition on individual logs. This could be a separate atomic step (`satisfy`) or a separate feature entirely.

### Audit Trail

Tags carry provenance (author, timestamp, reason), which provides per-log audit info. A centralized audit log (e.g., "these 47 logs were promoted at time T by user X") is out of scope for this feature. `validate` doesn't need provenance since it doesn't mutate anything. `copy` could optionally record provenance in the future (e.g., tag the source log with "promoted_to: s3://...").

### Post-run hooks

A natural extension is integrating workflow steps with `flow run` — automatically run QA or promotion steps after evaluations complete. This could be a `FlowSpec` configuration:

```yaml
post_run:
  - step: qa
  - step: promote
    args:
      dest: s3://my-org/prod/golden
```

This would enable fully automated pipelines: run evals → QA scores → tag results → promote golden logs, all from a single `flow run` invocation.

## TODOs (Alex)

- [ ] Add a composition example using `evals_df` to operate on log headers (e.g., find max score across a set of logs).
- [ ] Collect real-world QA workflow examples to validate the atomic step design: Inspect Scout scanners, multi-stage approval pipelines, integration with external tools.
- [ ] Figure out how to expose `validate` (and similar non-step functions) via the CLI — since `validate` doesn't fit `@step`, it likely needs a separate decorator (e.g., `@command`) that registers a CLI command without the step read/write lifecycle.
