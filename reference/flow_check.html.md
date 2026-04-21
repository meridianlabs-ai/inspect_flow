# flow_check – Inspect Flow

Check a spec against existing logs (searches log directory recursively)

#### Usage

``` text
flow check [OPTIONS] CONFIG_FILE
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--venv` | boolean | If set, resolve tasks in a virtual environment in a temporary directory. | `False` |
| `--limit` | integer | Set the expected number of samples per task for completeness calculation. | None |
| `--log-dir` | directory | Set the log directory. Will override the `log_dir` specified in the config. | None |
| `--arg`, `-A` | text | Set arguments that will be passed as kwargs to the function in the flow config. Only used when the last statement in the config file is a function. Examples: `--arg task_min_priority=2` If the same key is provided multiple times, later values will override earlier ones. | None |
| `--set`, `-s` | text | Override any field in the flow config using dot notation (e.g. `field.subfield=value`). The path corresponds to the fields of [FlowSpec](../reference/inspect_flow.html.md#flowspec) and its nested types (`options`, `defaults`, `tasks`, etc.). Examples: `--set options.limit=10` `--set defaults.solver.args.tool_calls=none` `--set options.metadata={"key1": "val1", "key2": "val2"}` Values are parsed as JSON when possible (lists and dicts), otherwise as strings. String values are appended to existing lists; JSON lists and dicts replace existing values. When the same key is provided multiple times, later values override earlier ones. | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'rich'`). | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
| `--help` | boolean | Show this message and exit. | `False` |
