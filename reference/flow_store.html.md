# flow store


Manage the flow store

#### Usage

``` text
flow store [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

|                              |                                            |
|------------------------------|--------------------------------------------|
| [import](#flow-store-import) | Import logs into the store                 |
| [remove](#flow-store-remove) | Remove logs from the store                 |
| [info](#flow-store-info)     | Print store information                    |
| [delete](#flow-store-delete) | Delete the flow store                      |
| [list](#flow-store-list)     | List logs and log directories in the store |

## flow store import

Import logs into the store

#### Usage

``` text
flow store import [OPTIONS] PATH...
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--store`, `-s` | directory | Path to the store directory | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to ‘full’) | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--recursive`, `-r` / `--no-recursive`, `-R` | boolean | Search directories recursively for logs | `True` |
| `--copy-from` | directory | Copy logs from this directory to PATH before importing. | None |
| `--dry-run` | boolean | Preview what would be imported without making changes | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## flow store remove

Remove logs from the store

#### Usage

``` text
flow store remove [OPTIONS] [PREFIX]...
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--store`, `-s` | directory | Path to the store directory | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to ‘full’) | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--recursive`, `-r` / `--no-recursive`, `-R` | boolean | Search directories recursively for logs | `True` |
| `--missing` | boolean | Remove logs that no longer exist on file system | `False` |
| `--dry-run` | boolean | Preview what would be removed without making changes | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## flow store info

Print store information

#### Usage

``` text
flow store info [OPTIONS]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--store`, `-s` | directory | Path to the store directory | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to ‘full’) | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--help` | boolean | Show this message and exit. | `False` |

## flow store delete

Delete the flow store

#### Usage

``` text
flow store delete [OPTIONS]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--store`, `-s` | directory | Path to the store directory | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to ‘full’) | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--yes`, `-y` | boolean | Skip confirmation prompt | `False` |
| `--help` | boolean | Show this message and exit. | `False` |

## flow store list

List logs and log directories in the store

#### Usage

``` text
flow store list [OPTIONS]
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--store`, `-s` | directory | Path to the store directory | None |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to ‘full’) | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to ‘warning’) | `warning` |
| `--format` | choice (`flat` \| `tree`) | Output format: tree, flat | `flat` |
| `--help` | boolean | Show this message and exit. | `False` |
