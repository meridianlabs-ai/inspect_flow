# flow_step – Inspect Flow

Run workflow steps on eval logs.

Steps are discovered from built-in steps, \_flow.py files in the current directory tree, and Python entry points.

You can also load steps from an arbitrary Python file:

    flow step file.py --help          List steps in a file

    flow step file.py STEP [ARGS]     Run a step from a file

    flow step file.py@STEP [ARGS]     Shorthand for the above

#### Usage

``` text
flow step [OPTIONS] COMMAND [ARGS]...
```

#### Subcommands

|  |  |
|----|----|
| [copy](#flow-step-copy) | Copy eval logs to a destination directory. |
| [metadata](#flow-step-metadata) | Set or delete metadata fields on eval logs. |
| [scan](#flow-step-scan) | Run Inspect Scout scanners against the transcripts of eval logs. |
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
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'full'`). | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
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
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'full'`). | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
| `--help` | boolean | Show this message and exit. | `False` |

## flow step scan

Run Inspect Scout scanners against the transcripts of eval logs.

#### Usage

``` text
flow step scan [OPTIONS] [PATH]...
```

#### Options

| Name | Type | Description | Default |
|----|----|----|----|
| `--scanners` | text | Scanners to run, as a sequence, dict, `ScanJob`, `ScanJobConfig`, or a path to a Python/YAML file containing scanjob/scanner definitions. | \_required |
| `-S` | text | One or more scanjob or scanner arguments (e.g. -S arg=value) | None |
| `--scans` | text | Location to write scan results to. Defaults to a ‘scans’ directory alongside the input logs (errors if logs are in multiple directories). | None |
| `-V`, `--validation` | text | One or more validation sets to apply for scanners (e.g. -V myscanner:deception.csv) | None |
| `--model` | text | Model used by default for llm scanners. | None |
| `--model-base-url` | text | Base URL for for model API | None |
| `-M` | text | One or more native model arguments (e.g. -M arg=value) | None |
| `--model-config` | text | YAML or JSON config file with model arguments. | None |
| `--model-role` | text | Named model role with model name or YAML/JSON config, e.g. –model-role critic=openai/gpt-4o or –model-role grader=“{model: mockllm/model, temperature: 0.5}” | None |
| `--max-transcripts` | integer | Maximum number of transcripts to scan concurrently (defaults to 25) | None |
| `--max-processes` | integer | Number of worker processes. Defaults to 4. | None |
| `--limit` | integer | Limit number of transcripts to scan. | None |
| `--shuffle` | text | Shuffle order of transcripts (pass a seed to make the order deterministic) | None |
| `--tags` | text | Tags to associate with this scan job (comma separated) | None |
| `--metadata` | text | Metadata to associate with this scan job (more than one –metadata argument can be specified). | None |
| `--cache` | text | Policy for caching of model generations. Specify –cache to cache with 7 day expiration (7D). Specify an explicit duration (e.g. (e.g. 1h, 3d, 6M) to set the expiration explicitly (durations can be expressed as s, m, h, D, W, M, or Y). Alternatively, pass the file path to a YAML or JSON config file with a full `CachePolicy` configuration. | None |
| `--batch` | text | Batch requests together to reduce API calls when using a model that supports batching (by default, no batching). Specify –batch to batch with default configuration, specify a batch size e.g. `--batch=1000` to configure batches of 1000 requests, or pass the file path to a YAML or JSON config file with batch configuration. | None |
| `--max-connections` | integer | Maximum number of concurrent connections to Model API (defaults to max_transcripts) | None |
| `--max-retries` | integer | Maximum number of times to retry model API requests (defaults to unlimited) | None |
| `--timeout` | integer | Model API request timeout in seconds (defaults to no timeout) | None |
| `--max-tokens` | integer | The maximum number of tokens that can be generated in the completion (default is model specific) | None |
| `--temperature` | float | What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. | None |
| `--top-p` | float | An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. | None |
| `--top-k` | integer | Randomly sample the next word from the top_k most likely next words. Anthropic, Google, HuggingFace, and vLLM only. | None |
| `--reasoning-effort` | choice (`minimal` \| `low` \| `medium` \| `high`) | Constrains effort on reasoning for reasoning models (defaults to `medium`). Open AI o-series and gpt-5 models only. | None |
| `--reasoning-tokens` | integer | Maximum number of tokens to use for reasoning. Anthropic Claude models only. | None |
| `--reasoning-summary` | choice (`concise` \| `detailed` \| `auto`) | Provide summary of reasoning steps (defaults to no summary). Use ‘auto’ to access the most detailed summarizer available for the current model. OpenAI reasoning models only. | None |
| `--reasoning-history` | choice (`none` \| `all` \| `last` \| `auto`) | Include reasoning in chat message history sent to generate (defaults to “auto”, which uses the recommended default for each provider) | None |
| `--fail-on-error` | boolean | Re-raise exceptions instead of capturing them in results | `False` |
| `--store` | text | Resolve logs from a store. Use –store for the default store or –store PATH for a specific one. | None |
| `--filter` | text | Log filter. Only process logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times (all must pass). | None |
| `--exclude` | text | Log filter. Exclude logs that pass. Accepts a registered name, `file.py@name`, or a name defined in `_flow.py`. Can be used multiple times. | None |
| `--recursive` / `--no-recursive` | boolean | Recurse into directories (default: true). No effect when –store is used. | `True` |
| `--dry-run` | boolean | Preview changes without writing to disk. | `False` |
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'full'`). | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
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
| `--display` | choice (`full` \| `rich` \| `plain`) | Set the display mode (defaults to `'full'`). | `full` |
| `--log-level` | choice (`debug` \| `trace` \| `http` \| `info` \| `warning` \| `error` \| `critical` \| `notset`) | Set the log level (defaults to `'warning'`). | `warning` |
| `--help` | boolean | Show this message and exit. | `False` |
