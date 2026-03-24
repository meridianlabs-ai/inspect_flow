# flow run


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
| `--log-dir-create-unique` | boolean | If set, create a unique log directory by appending a datetime subdirectory (e.g. `2025-12-09T17-36-43`) under the specified `log_dir`. If not set, use the existing `log_dir` (which must be empty or have `log_dir_allow_dirty=True`). | `False` |
| `--log-dir` | directory | Set the log directory. Will override the `log_dir` specified in the config. | None |
| `--store-write` / `--no-store-write` | boolean | Write completed logs to the store (default: `--store-write`). | None |
| `--store-read` / `--no-store-read` | boolean | Read existing logs from the store (default: `--no-store-read`). | None |
| `--store-filter` | text | Log filter to apply when searching the store for existing logs. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass). | None |
| `--store` | directory | Path to the store directory. Will override the store specified in the config. `'auto'` for default location. `'none'` for no store. | None |
| `--limit` | integer | Limit the number of samples to run. | None |
| `--arg`, `-A` | text | Set arguments that will be passed as kwargs to the function in the flow config. Only used when the last statement in the config file is a function. Examples: `--arg task_min_priority=2` If the same key is provided multiple times, later values will override earlier ones. | None |
| `--set`, `-s` | text | Set config overrides. Examples: `--set defaults.solver.args.tool_calls=none` `--set options.limit=10` `--set options.metadata={"key1": "val1", "key2": "val2"}` The specified value may be a string or json parsable list or dict. If string is provided then it will be appended to existing list values. If json list or dict is provided then it will replace existing values. If the same key is provided multiple times, later values will override earlier ones. | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'rich'`). | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
| `--help` | boolean | Show this message and exit. | `False` |
