# flow_run – Inspect Flow

Run a spec

#### Usage

``` text
flow run [OPTIONS] CONFIG_FILE
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--dry-run` | boolean | Do not run spec, but show a count of tasks that would be run. | `False` |
| `--log-dir-allow-dirty` | boolean | Do not fail if the `log-dir` contains files that are not part of the eval set. | `False` |
| `--venv` | boolean | If set run the flow in a virtual environment in a temporary directory. | `False` |
| `--resume` | boolean | Resume from the previous run by reusing its log directory. Mutually exclusive with `--log-dir`. | `False` |
| `--log-dir-create-unique` / `--no-log-dir-create-unique` | boolean | If set, create a unique log directory by appending a datetime subdirectory (e.g. `2025-12-09T17-36-43`) under the specified `log_dir`. If not set, use the existing `log_dir` (which must be empty or have `log_dir_allow_dirty=True`). | None |
| `--store-write` / `--no-store-write` | boolean | Write completed logs to the store (default: `--store-write`). | None |
| `--store-read` / `--no-store-read` | boolean | Read existing logs from the store (default: `--no-store-read`). | None |
| `--store-filter` | text | Log filter to apply when searching the store for existing logs. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass). | None |
| `--store` | text | Path to the store directory. Will override the store specified in the config. `'auto'` for default location. `'none'` for no store. | None |
| `--limit` | integer | Limit the number of samples to run. | None |
| `--log-dir` | directory | Set the log directory. Will override the `log_dir` specified in the config. | None |
| `--arg`, `-A` | text | Set arguments that will be passed as kwargs to the function in the flow config. Only used when the last statement in the config file is a function. Examples: `--arg task_min_priority=2` If the same key is provided multiple times, later values will override earlier ones. | None |
| `--set`, `-s` | text | Override any field in the flow config using dot notation (e.g. `field.subfield=value`). The path corresponds to the fields of [FlowSpec](../reference/inspect_flow.html.md#flowspec) and its nested types (`options`, `defaults`, `tasks`, etc.). Examples: `--set options.limit=10` `--set defaults.solver.args.tool_calls=none` `--set options.metadata={"key1": "val1", "key2": "val2"}` Values are parsed as JSON when possible (lists and dicts), otherwise as strings. String values are appended to existing lists; JSON lists and dicts replace existing values. When the same key is provided multiple times, later values override earlier ones. | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'rich'`). | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
| `--help` | boolean | Show this message and exit. | `False` |
