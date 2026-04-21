# flow_step – Inspect Flow

Run workflow steps on eval logs.

Steps are discovered from built-in steps, \_flow.py files in the current directory tree, and Python entry points.

You can also load steps from an arbitrary Python file:

flow step file.py –help List steps in a file flow step file.py STEP \[ARGS\] Run a step from a file flow step <file.py@STEP> \[ARGS\] Shorthand for the above

#### Usage

``` text
flow step [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

|  |  |
|----|----|
| [copy](#flow-step-copy) | Copy eval logs to a destination directory. |
| [metadata](#flow-step-metadata) | Set or delete metadata fields on eval logs. |
| [tag](#flow-step-tag) | Add or remove tags on eval logs. |

## flow step copy

Copy eval logs to a destination directory.

#### Usage

``` text
flow step copy [OPTIONS] [PATH]...
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--dest` | text | Destination directory (local or S3). | \_required |
| `--source-prefix` | text | Directory prefix to strip from source paths. Without this option, files are copied flat into the destination. When provided, preserves directory structure relative to the prefix. | None |
| `--overwrite` | boolean | Overwrite existing files at the destination. | `False` |
| `--store` | text | Resolve logs from a store. Use –store for the default store or –store PATH for a specific one. | None |
| `--filter` | text | Log filter. Only process logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass). | None |
| `--exclude` | text | Log filter. Exclude logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times. | None |
| `--recursive` / `--no-recursive` | boolean | Recurse into directories (default: true). No effect when –store is used. | `True` |
| `--dry-run` | boolean | Preview changes without writing to disk. | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## flow step metadata

Set or delete metadata fields on eval logs.

#### Usage

``` text
flow step metadata [OPTIONS] [PATH]...
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--set` | text | Key-value pairs to set. | `()` |
| `--remove` | text | Keys to delete. | `()` |
| `--author` | text | Provenance author. Defaults to git user. | None |
| `--reason` | text | Reason for the edit. | None |
| `--store` | text | Resolve logs from a store. Use –store for the default store or –store PATH for a specific one. | None |
| `--filter` | text | Log filter. Only process logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass). | None |
| `--exclude` | text | Log filter. Exclude logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times. | None |
| `--recursive` / `--no-recursive` | boolean | Recurse into directories (default: true). No effect when –store is used. | `True` |
| `--dry-run` | boolean | Preview changes without writing to disk. | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## flow step tag

Add or remove tags on eval logs.

#### Usage

``` text
flow step tag [OPTIONS] [PATH]...
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--add` | text | Tags to add. | `()` |
| `--remove` | text | Tags to remove. | `()` |
| `--author` | text | Provenance author. Defaults to git user. | None |
| `--reason` | text | Reason for the edit. | None |
| `--store` | text | Resolve logs from a store. Use –store for the default store or –store PATH for a specific one. | None |
| `--filter` | text | Log filter. Only process logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass). | None |
| `--exclude` | text | Log filter. Exclude logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times. | None |
| `--recursive` / `--no-recursive` | boolean | Recurse into directories (default: true). No effect when –store is used. | `True` |
| `--dry-run` | boolean | Preview changes without writing to disk. | `False` |
| `--help` | boolean | Show this message and exit. | `False` |
