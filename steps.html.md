# Steps – Inspect Flow

Steps are operations you run on evaluation logs *after* `flow run` completes. Use them to tag logs, set metadata, copy logs between directories, validate results, or compose these into multi-stage workflows like QA pipelines.

## The `flow step` Command

Run a step on logs in a directory:

``` bash
flow step tag logs/ --add reviewed
```

Steps are discovered automatically from built-in steps and `@step` functions defined or imported in `_flow.py` files in the current directory tree. To see all available steps:

``` bash
flow step --help
```

### Common options

All steps share these options:

| Option | Description |
|----|----|
| `PATH` | Log paths or directories to process (local or S3) |
| `--store` | Resolve logs from a store (mutually exclusive with PATH) |
| `--filter` | Only process logs that pass a [filter](#filtering). Accepts registered names, `file.py@name`, or names defined in `_flow.py`. Can be used multiple times (all must pass) |
| `--exclude` | Skip logs that pass a filter (can be used multiple times) |
| `--recursive/--no-recursive` | Recurse into directories (default: true) |
| `--dry-run` | Preview changes without writing to disk |

## Built-in Steps

### [**tag**](./reference/inspect_flow.api.html.md#tag)

Add or remove tags on eval logs:

``` bash
flow step tag logs/ --add reviewed --add golden
flow step tag logs/ --remove draft
flow step tag logs/ --add approved --reason "Passed QA"
```

### [**metadata**](./reference/inspect_flow.api.html.md#metadata)

Set or remove metadata fields on eval logs:

``` bash
flow step metadata logs/ --set score=0.95 --set stage=production
flow step metadata logs/ --remove draft_notes
```

Values are parsed as JSON where possible (`--set count=42` sets an integer, `--set name=foo` sets a string, `--set 'scan={"model": "gpt-4o", "config": {"threshold": 0.8}}'` sets a nested dict).

### Provenance

Both `tag` and `metadata` record provenance on every edit — a timestamp, author, and optional reason. The author defaults to your git user (`git config user.name` and `user.email`). You can override it with `--author` and provide a `--reason` for auditability:

``` bash
flow step tag logs/ --add reviewed --author "CI Bot" --reason "Nightly QA pass"
```

### [**copy**](./reference/inspect_flow.api.html.md#copy)

Copy eval logs to a destination directory:

``` bash
flow step copy logs/ --dest s3://bucket/prod/
flow step copy logs/ --dest ./archive/ --source-prefix ./logs/
```

Without `--source-prefix`, files are copied flat into the destination. With it, directory structure relative to the prefix is preserved. Use `--overwrite` to replace existing files. Use `--store` to add copied logs to the Flow Store index.

## Custom Steps

Define custom steps with the `@step` decorator. A step is a function that takes a `list[EvalLog]` and returns a `list[EvalLog]`:

``` python
from inspect_ai.log import EvalLog
from inspect_flow import step
from inspect_flow.api import tag, metadata

@step
def review_scores(
    logs: list[EvalLog],
    *,
    min_score: float = 0.8,
) -> list[EvalLog]:
    """Tag logs that meet a score threshold and record it in metadata.

    Args:
        min_score: Minimum score to pass review.
    """
    passing = [log for log in logs if (log.results.scores[0].value or 0) >= min_score]
    passing = tag(passing, add=["passing"])
    return metadata(passing, set={"min_score": min_score})
```

The function’s keyword arguments are automatically converted to CLI options:

``` bash
flow step review_scores logs/ --min-score 0.9
```

Parameter help text shown in `--help` is extracted from Google-style docstrings.

> **NOTE: Note**
>
> Steps receive log headers only — samples are not loaded. To access samples in a custom step, use [`read_eval_log()`](https://inspect.aisi.org.uk/reference/inspect_ai.html#read_eval_log) from Inspect AI with `header_only=False`.

### Nesting and deferred writes

Steps can call other steps — as shown in `review_scores` above. When steps are nested, writes are deferred until the outermost step exits. This means a composed workflow either completes fully or not at all.

### StepResult

Steps can return a plain `list[EvalLog]` or a [StepResult](./reference/inspect_flow.api.html.md#StepResult) for finer control:

| Field | Default | Description |
|----|----|----|
| `logs` |  | The logs returned to the caller |
| `modified` | `True` | When `False`, logs are not written back to disk |
| `flush` | `False` | Write all dirty logs immediately, bypassing [deferred writes](#nesting-and-deferred-writes) |
| `skip_log_steps` | `False` | Skip remaining steps for this log |

``` python
from inspect_flow.api import StepResult

@step
def audit(logs: list[EvalLog]) -> StepResult:
    """Print a summary of log statuses."""
    for log in logs:
        print(f"{log.eval.task}: {log.status}")
    return StepResult(logs=logs, modified=False)
```

## Step Discovery

Steps are discovered from multiple sources:

1.  **Built-in steps** — `tag`, `metadata`, `copy`
2.  **`_flow.py` files** — any `@step` functions defined or imported in `_flow.py` files in the current directory or parent directories are automatically discovered (same [automatic discovery](./defaults.html.md#automatic-discovery) as for defaults)
3.  **Arbitrary files** — load steps from any Python file, without needing them in `_flow.py`:

``` bash
flow step file.py --help            # List steps defined in a file
flow step file.py step_name [ARGS]  # Run a step from a file
flow step file.py@step_name [ARGS]  # Shorthand for the above
```

For team workflows, import your steps in a `_flow.py` at the repository root so they’re discoverable by all team members:

``` python
# _flow.py
from my_project.steps import promote, review_scores  # noqa: F401
```

## Filtering

Use `@log_filter` to define named functions that select logs based on their properties:

``` python
from inspect_ai.log import EvalLog
from inspect_flow import log_filter

@log_filter
def reviewed(log: EvalLog) -> bool:
    """True when a log has been reviewed."""
    return "review_done" in log.tags and "review_needed" not in log.tags

@log_filter
def promoted(log: EvalLog) -> bool:
    """True when a log has been marked as golden."""
    return "golden" in log.tags
```

Filters can be used with `flow step` via the `--filter` and `--exclude` options:

``` bash
# Only process reviewed logs
flow step promote logs/ --filter reviewed

# Process all reviewed logs except those already marked golden
flow step tag logs/ --filter reviewed --exclude promoted --add golden
```

The same `@log_filter` functions work across Flow — with [`flow list log`](./reference/flow_list.html.md), [`flow run --store-filter`](./store.html.md#filtering), and store commands. Like steps, filters defined or imported in `_flow.py` files are automatically discovered.

## Checking Completeness

The [`flow check`](./reference/flow_check.html.md) command checks the completeness of a spec against existing logs in a directory. Its primary use is checking against a different log directory than the one in the spec — for example, checking how complete a production directory is:

``` bash
flow check spec.py --log-dir /path/to/prod/logs
```

This instantiates tasks from the spec, searches the target directory recursively for matching logs, and reports:

- A table of tasks with their matched log file, completed samples, and tags
- Duplicate logs (older logs superseded by newer ones)
- Unexpected logs (files that don’t match any task in the spec)
- A summary line: e.g. `Check: 25/27 tasks complete (2 logs incomplete)`

Unlike `flow run --dry-run`, `flow check` does not use the Flow Store — it only searches the specified log directory.

### Python API

``` python
from inspect_flow.api import check, load_spec

spec = load_spec("spec.py")
result = check(spec, log_dir="/path/to/prod/logs")
for task in result.tasks:
    print(f"{task.name}: {task.samples}/{task.total_samples}")
```

## Example: Review and Promote Workflow

Here’s a complete workflow combining steps, filters, and check to manage evaluations from development through to production.

**Define a filter** (`filters.py`):

``` python
from inspect_ai.log import EvalLog
from inspect_flow import log_filter

@log_filter
def reviewed(log: EvalLog) -> bool:
    """True when a log has been reviewed."""
    return "review_done" in log.tags and "review_needed" not in log.tags
```

**Define steps** (`steps.py`):

``` python
from inspect_ai.log import EvalLog
from inspect_flow import step
from inspect_flow.api import tag, copy
from my_project.filters import reviewed

@step
def mark_reviewed(logs: list[EvalLog]) -> list[EvalLog]:
    """Mark logs as manually reviewed."""
    return tag(logs, add=["review_done"], remove=["review_needed"])

@step
def promote(logs: list[EvalLog]) -> list[EvalLog]:
    """Promote reviewed logs to production."""
    logs = [log for log in logs if reviewed(log)]
    logs = tag(logs, add=["promoted"], reason="Passed review")
    return copy(logs, dest="s3://bucket/prod/logs")
```

**Import for discovery** (`_flow.py`):

``` python
from my_project.filters import reviewed  # noqa: F401
from my_project.steps import mark_reviewed, promote  # noqa: F401
```

**Run the workflow:**

``` bash
# 1. Check if logs already exist (from teammates, previous runs, etc.)
flow check spec.py --log-dir s3://bucket/dev/logs/

# 2. Run evaluations (logs written to e.g. s3://bucket/dev/logs/2026-04-14T10-30-00/)
flow run spec.py

# 3. Review in Viewer
inspect view --log-dir s3://bucket/dev/logs/2026-04-14T10-30-00/

# 4. Mark as reviewed
flow step mark_reviewed s3://bucket/dev/logs/2026-04-14T10-30-00/

# 5. Promote to production
flow step promote s3://bucket/dev/logs/2026-04-14T10-30-00/

# 6. Verify production completeness
flow check spec.py --log-dir s3://bucket/prod/logs/
```

## Python API

The same workflow can be run programmatically via `inspect_flow.api`:

``` python
from inspect_flow.api import check, load_spec, run_step
from my_project.steps import mark_reviewed, promote

run_dir = "s3://bucket/dev/logs/2026-04-14T10-30-00/"

run_step(mark_reviewed, run_dir)
run_step(promote, run_dir)
```

See the [API Reference](./reference/inspect_flow.api.html.md) for complete documentation.
