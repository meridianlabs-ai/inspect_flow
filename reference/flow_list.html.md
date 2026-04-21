# flow_list – Inspect Flow

CLI command to list flow entities.

#### Usage

``` text
flow list [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

|  |  |
|----|----|
| [log](#flow-list-log) | List logs, sorted by timestamp extracted from log file name. If PATH is not provided, falls back to the default store (–store auto). |

## flow list log

List logs, sorted by timestamp extracted from log file name. If PATH is not provided, falls back to the default store (–store auto).

#### Usage

``` text
flow list log [OPTIONS] [PATH]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--store` | text | Path to the store directory. | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'rich'`). | `rich` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
| `--exclude` | text | Log filter. Include only logs that do NOT pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. | None |
| `--filter` | text | Log filter. Include only logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass). | None |
| `--format` | choice (`table` \| `tree`) | Output format | `table` |
| `--oneline` | boolean | Show each log on a single line (compact table format). | `False` |
| `--provenance` | boolean | Show provenance (edit history) for each log. Only displayed in multiline mode. | `False` |
| `--no-page` | boolean | Disable paged output. | `False` |
| `-n`, `--max-count` | integer | Limit output to N logs. Also accepts -N (e.g. -5). | None |
| `--task` | text | Only show logs whose task name matches PATTERN (glob). May be repeated. | None |
| `--model` | text | Only show logs whose model matches PATTERN (glob). May be repeated. | None |
| `--tag` | text | Only show logs with a tag matching PATTERN (glob). May be repeated. | None |
| `--status` | choice (`success` \| `error` \| `cancelled` \| `started`) | Only show logs with this status. May be repeated. | None |
| `--live` | integer | Refresh display every N seconds (default: 10). | None |
| `--since`, `--after` | text | Only show logs whose filename timestamp is at or after DATE. Date strings like `'2024-01-15'` resolve to midnight; relative expressions like `'today'` resolve to the current time. | None |
| `--until`, `--before` | text | Only show logs whose filename timestamp is at or before DATE. Date strings like `'2024-06-01'` resolve to midnight; relative expressions like `'yesterday'` resolve to the current time minus one day. | None |
| `--help` | boolean | Show this message and exit. | `False` |
