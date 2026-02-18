# Store Design

## Overview

The store is a **cache** that indexes Inspect AI evaluation log files by task identifier. It speeds up finding completed evaluations across runs so they don't need to be re-executed. The store does not contain log data itself — only pointers (file paths) to log files. If the store is lost or corrupted, it can always be rebuilt by re-importing logs from their original locations via `flow store import`.

## Data Model

The store contains a single entity: the **logs table**. Each row maps a `log_path` to a `task_identifier` and a timestamp. There are no other tables, indices, or entities. The log path is the canonical identifier for a log file (stored as a URI), and the task identifier is a content-based hash computed by Inspect AI from the task definition and eval parameters.

## Storage Backend

The store uses [Delta Lake](https://delta.io/) (via the `deltalake` Python library with PyArrow). Delta Lake was chosen because:

- It works on both local filesystems and S3 without code changes.
- It supports concurrent writes safely (important for shared S3 stores).
- It uses Parquet columnar storage, which is efficient for the filtering queries the store performs.

The store is laid out as:
```
<store_path>/flow_store/_table_logs/   # Delta Lake table
```

## Versioning

Each table carries a semver version in its Delta Lake description metadata (e.g., `"0.2.0"`). Version compatibility follows these rules:

| Version change | Meaning |
|---|---|
| **Major** bump | Breaking change. Old code cannot read or write the store. |
| **Minor** bump | Old code cannot read the store (new features it doesn't understand). |
| **Patch** bump | Backward compatible. Old code can still read and write. |

On startup, the store reads the stored version and compares it against the version the code expects. If the stored version is too new (major or minor exceeds what the code supports), the store raises an error directing the user to upgrade.

## Task Identifier Versioning

The task identifier is computed by Inspect AI and may change its format across versions. Rather than migrating all existing rows when the format changes, the store uses **versioned columns**: `task_identifier_1`, `task_identifier_2`, etc. Each column corresponds to a specific version of the identifier algorithm.

When the code needs to query by task identifier:
1. It checks which column matches the current `TASK_IDENTIFIER_VERSION`.
2. Rows with a missing value in that column are backfilled on demand by reading the log header and recomputing the identifier (`_set_task_identifiers`).

This means old stores gradually gain new identifier columns as they're accessed, without requiring a migration step.

## Error Handling Philosophy

The store should never add friction to the user's workflow. If the store is unavailable or a stored log path is inaccessible, the store silently degrades:

- `store_factory` returns `None` if the store doesn't exist — the runner proceeds without it.
- `search_for_logs` skips individual log files that fail to read, logging at info level only.
- `add_run_logs` failures after a completed eval are caught and logged, never surfacing to the user.

The principle: a cache failure should never block or interrupt an evaluation run. The store is purely additive — its absence means some evaluations may be re-run, but correctness is never affected.
