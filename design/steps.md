## Problem

After `flow run` produces eval logs, users need to QA and promote them through diverse, org-specific workflows. Examples: tag logs as QA'd, validate that scores meet thresholds, copy golden logs to a production S3 bucket. No single workflow fits all teams, so we need composable atomic steps.

## Atomic Steps

A step is a function that operates on a single `EvalLog` and returns the modified log (or signals to stop). Steps are run one file at a time to avoid loading all logs into memory — log files can be large. The `run_step` helper (see [_steps/run.py](../src/inspect_flow/_steps/run.py)) iterates over paths/logs and calls the step for each one.

Three operations that users compose into workflows:

| Step | Purpose | Output |
|---|---|---|
| `tag` | Add/remove tags on log files | Modified source logs |
| `metadata` | Set/delete metadata fields on log files | Modified source logs |
| `copy` | Copy log files to another location | New destination logs |

> Filtering (selecting a subset of logs) is not a step — it's handled by `run_step`'s `filter` parameter or `--filter` on the CLI. Filters use the `@log_filter` registry (see [store_filters.md](store_filters.md)). Multiple filters can be combined (all must pass).

> Validation (asserting conditions on logs) is not a step — it doesn't modify logs and has no meaningful "set of modified logs" to pass forward. Use `validate()` as a standalone function call within a step or script.

## Dependencies

The `tag` and `metadata` steps depend on Inspect AI's [log editing API](https://inspect.aisi.org.uk/reference/inspect_ai.log.html#log-editing) (`edit_eval_log`, `TagsEdit`, `MetadataEdit`, `ProvenanceData`).

`validate` and user-defined filtering use `LogFilter = Callable[[EvalLog], bool]` and the `@log_filter` registry from [store_filters.md](store_filters.md).

## Execution Model

Steps operate on one log at a time. Callers pass either a file path or an `EvalLog` object — `@step` handles path resolution transparently, so each step implementation only receives a single `EvalLog`. The step returns an `EvalLog` (modified log), `StepResult` (for fine-grained control), or `None` (to stop processing).

```python
# Caller passes a path — @step reads the full log, calls tag(EvalLog), writes back
tag("./logs/2026-03-11/log1.eval", add=["reviewed"])

# Caller passes an EvalLog — @step passes it through directly
log = tag(log, add=["golden"])                      # returns EvalLog
log = copy(log, dest="s3://my-org/prod/golden")     # returns destination EvalLog
```

To run a step across multiple logs, use `run_step` (see [_steps/run.py](../src/inspect_flow/_steps/run.py)):

```python
# run_step iterates over paths/logs and calls the step for each one
run_step(tag, "./logs/2026-03-11/", add=["reviewed"])

# From store — caller resolves paths, run_step handles the rest
run_step(tag, store.get_logs(filter=my_filter), add=["reviewed"])
```

Nested steps accumulate into the outermost step's dirty set via a `ContextVar`. Only the outermost step performs disk writes.

### `@step` decorator params

```python
@step                           # header_only=True (default) — step receives header-only EvalLog
@step(header_only=False)        # step receives full EvalLog including samples
```

### `StepResult`

Steps can return an `EvalLog`, `None`, or a `StepResult` for fine-grained control. See [_steps/step.py](../src/inspect_flow/_steps/step.py) for the full type definition and docstring.

### How `copy` works

`copy` is decorated with `@step(header_only=False)` so it receives the full `EvalLog` including samples. It uses `model_copy(update={"location": dest_path})` to create a new `EvalLog` pointing at the destination — no I/O, no header merging. `@step` writes the destination log as part of its dirty set.

### Exceptions during steps

An exception during a step stops all further processing — the current log and any remaining logs in the `run_step` batch are not processed. Logs already written by previous iterations are unaffected, and no files are modified for the current log.

### How `@step` manages the lifecycle

```
1. @step receives a single path or EvalLog
2. If a path: reads the full log from disk (always header_only=False for the read)
3. If header_only=True: strips samples/reductions before passing to the step function
4. Calls the step function with a single EvalLog
5. If header_only=True: reattaches samples/reductions to the returned log
6. Tracks modified logs in the dirty set (ContextVar)
7. If outermost step (or flush=True): writes all dirty logs and clears the set
8. Returns the log (or None if skip_log_steps)
```

### `run_step`

`run_step` (see [_steps/run.py](../src/inspect_flow/_steps/run.py)) iterates over multiple logs/paths and calls a step function on each one. This is what the CLI uses, and the primary way to apply a step across a batch of logs.

```python
run_step(step, logs, dry_run=False, filter=None, recursive=True, *args, **kwargs)
```

`logs` can be a single path, a single `EvalLog`, or a sequence of either. Directories are expanded recursively by default (`recursive=False` to disable). `filter` accepts a callable, registered name, `"file.py@name"` string, or a sequence of any of these (all must pass). `dry_run=True` runs steps but skips writing to disk.

## Log Resolution

Steps accept a log path or an EvalLog object, not store queries. Users who want to pull from the store do so explicitly:

```python
store = store_get()
run_step(tag, store.get_logs(filter=my_filter), add=["reviewed"])
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

See [_steps/tag.py](../src/inspect_flow/_steps/tag.py). Applies `TagsEdit` via `edit_eval_log`. Provenance defaults to git `user.name <user.email>` if not provided.

### `metadata`

See [_steps/tag.py](../src/inspect_flow/_steps/tag.py). Applies `MetadataEdit` via `edit_eval_log`. Same provenance defaults as `tag`.

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

See [_steps/copy.py](../src/inspect_flow/_steps/copy.py). Decorated with `@step(header_only=False)` — requires full logs. Uses `model_copy` to create destination `EvalLog` objects without mutating originals. Returns destination logs; subsequent steps operate on those, not the sources.

### Composition Examples

#### Chaining steps on a single log

Without an outer `@step`, each step call is its own outermost step — the log is passed in memory from step to step, but each step writes to disk immediately when it completes.

```python
from inspect_ai.log import read_eval_log

log = read_eval_log("./logs/2026-03-11/log1.eval")
log = tag(log, add=["golden"], reason="Promoted after QA")
# tag writes modified log to disk immediately
log = copy(log, dest="s3://my-org/prod/golden-logs")
# copy writes destination file to disk immediately
```

#### With `@step` (deferred writes)

Wrapping in `@step` defers all writes to the end — the log is passed in memory between nested steps, nothing is written until the outermost step completes, and nothing is persisted if the function raises.

```python
from inspect_flow import step
from inspect_flow.api import tag, copy, run_step, store_get

@step(header_only=False)  # required because copy needs full logs
def promote(log: EvalLog, *, dest: str = "s3://my-org/prod/golden") -> EvalLog:
    log = tag(log, add=["golden"], reason="Promoted after QA")
    return copy(log, dest=dest)
    # @step writes all dirty logs here

# Run across a directory
run_step(promote, "./logs/2026-03-11/", dest="s3://my-org/prod/golden")

# From store — caller resolves paths, run_step handles the rest
store = store_get()
run_step(promote, store.get_logs(filter=my_filter), dest="s3://my-org/prod/golden")
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
- `--store` (`-s`) — resolve logs from a store. Use `--store` for the default store or `--store PATH` for a specific one. Mutually exclusive with `PATH...`.
- `--filter` — registered `@log_filter` name to pre-filter which logs are passed to the step. Can be used multiple times (all must pass). Works with both `PATH...` and `--store`.
- `--recursive/--no-recursive` — recurse into directories (default: true)
- `--dry-run` — preview changes without writing to disk

For `tag` and `metadata`:
- `--author` — provenance author (default: git user)
- `--reason` — provenance reason

### User-Defined Steps

Users define reusable workflows with `@step`, which are also discoverable under `flow step`:

```python
from inspect_flow import step
from inspect_flow.api import tag, copy


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
def qa(log: EvalLog) -> EvalLog:
    """Automated QA: tag log as passed or failed based on scores."""
    if _scores_pass(log):
        return tag(log, add=["auto_qa_passed"], reason="Automated QA: scores passed")
    else:
        return tag(log, add=["auto_qa_failed"], reason="Automated QA: refusal or tool error")


@step(header_only=False)  # required because copy needs full logs
def promote(log: EvalLog, *, dest: str = "s3://my-org/prod/golden") -> EvalLog:
    """Promote a QA-passed log to golden storage."""
    log = tag(log, add=["golden"], reason="Promoted after automated QA")
    return copy(log, dest=dest)
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

- The first parameter (`EvalLog`) becomes the `PATH...` argument (the CLI uses `run_step` to iterate over paths).
- Type annotations drive click types (`str` → STRING, `int` → INT, `float` → FLOAT, `bool` → flag).
- Snake_case parameter names become --kebab-case on CLI.
- `--store`, `--filter`, `--recursive/--no-recursive`, and `--dry-run` are auto-injected on all `@step` CLI commands. `PATH...` and `--store` are mutually exclusive.

For example, `def promote(log, *, dest: str = "s3://...")` generates:

```
flow step promote PATH... --dest s3://...
flow step promote --store --filter my_filter --dest s3://...
flow step promote PATH... --dry-run --dest s3://...
```

## API Surface

### Public API (`_api/api.py`)

```python
from inspect_flow import step
from inspect_flow.api import tag, metadata, copy, run_step, StepResult
```

### CLI (`_cli/main.py`)

```python
flow.add_command(step_command)  # flow step tag|metadata|copy|<user-defined>
```

## Open Questions

### ~~1. Paths-only vs in-memory EvalLog composition~~ (Resolved)

Steps operate on one log at a time. `@step` accepts a path or `EvalLog`, reads the full log if needed, and writes back at the end. `run_step` handles iteration over multiple paths/logs.

### 2. Transactionality / Rollback

Steps are not transactional. The most important properties are:

- **Idempotency**: All steps should be safe to re-run. Tag/metadata edits are already idempotent (Inspect handles this). `copy` should support overwrite-or-skip behavior — consider a flag (e.g., `overwrite: bool`) to control whether existing files at the destination are overwritten or skipped.
- **Transparency on failure**: When a step errors mid-execution, logs should clearly report which changes were applied and which were not, so the user knows the state they're in.

### ~~3. Dirty tracking~~ (Resolved)

Steps return their modified logs. The outermost `@step` tracks these in a `ContextVar[dict[str, EvalLog]]` keyed by `log.location`, and writes all dirty logs when the function completes. See [_steps/step.py](../src/inspect_flow/_steps/step.py).

### ~~4. Step discovery~~ (Resolved)

`@step` registers functions in Inspect AI's global registry. The CLI scans `_flow.py` files (via `find_auto_includes`) and loads them, then queries the registry for all registered steps. See [_cli/step.py](../src/inspect_flow/_cli/step.py).

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
