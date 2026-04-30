"""Click options for the `flow step scan` CLI.

Copied from `inspect_scout._cli.scan.scan_command` (and its `@common_options`
decorator) so the flow step exposes the same flags as `scout scan`. Excludes:

- `-T/--transcripts`: the flow step sources transcripts from its log paths.
- `-F/--filter`: collides with flow's own `--filter` log filter.
- `--results`: deprecated in scout.
- `--dry-run`: collides with flow's `--dry-run`.
- `--response-schema`: declared in scout but never wired to the callback.
- `--log-level`, `--display`: provided by flow as common step options.

TODO: refactor inspect_scout to expose these options as a shared list and
import from there instead of maintaining a copy here.
"""

from typing import Any, Callable, TypeVar

import click
from inspect_ai._cli.util import (
    int_bool_or_str_flag_callback,
    int_or_bool_flag_callback,
)
from inspect_ai._util.constants import DEFAULT_CACHE_DAYS
from inspect_scout._util.constants import DEFAULT_BATCH_SIZE, DEFAULT_MAX_TRANSCRIPTS

F = TypeVar("F", bound=Callable[..., Any])


def scan_cli_options(func: F) -> F:
    """Apply scout `scan` CLI options to a step function via click decorators."""
    decorators = [
        click.option(
            "-S",
            multiple=True,
            type=str,
            envvar="SCOUT_SCAN_ARGS",
            help="One or more scanjob or scanner arguments (e.g. -S arg=value)",
        ),
        click.option(
            "--scans",
            type=str,
            default=None,
            help="Location to write scan results to. Defaults to a 'scans' "
            "directory alongside the input logs (errors if logs are in "
            "multiple directories).",
            envvar="SCOUT_SCAN_SCANS",
        ),
        click.option(
            "-V",
            "--validation",
            multiple=True,
            type=str,
            envvar="SCOUT_SCAN_VALIDATION",
            help="One or more validation sets to apply for scanners (e.g. -V myscanner:deception.csv)",
        ),
        click.option(
            "--model",
            type=str,
            help="Model used by default for llm scanners.",
            envvar="SCOUT_SCAN_MODEL",
        ),
        click.option(
            "--model-base-url",
            type=str,
            envvar="SCOUT_SCAN_MODEL_BASE_URL",
            help="Base URL for for model API",
        ),
        click.option(
            "-M",
            multiple=True,
            type=str,
            envvar="SCOUT_SCAN_MODEL_ARGS",
            help="One or more native model arguments (e.g. -M arg=value)",
        ),
        click.option(
            "--model-config",
            type=str,
            envvar="SCOUT_SCAN_MODEL_CONFIG",
            help="YAML or JSON config file with model arguments.",
        ),
        click.option(
            "--model-role",
            multiple=True,
            type=str,
            envvar="SCOUT_SCAN_MODEL_ROLE",
            help='Named model role with model name or YAML/JSON config, e.g. --model-role critic=openai/gpt-4o or --model-role grader="{model: mockllm/model, temperature: 0.5}"',
        ),
        click.option(
            "--max-transcripts",
            type=int,
            help=f"Maximum number of transcripts to scan concurrently (defaults to {DEFAULT_MAX_TRANSCRIPTS})",
            envvar="SCOUT_SCAN_MAX_TRANSCRIPTS",
        ),
        click.option(
            "--max-processes",
            type=int,
            help="Number of worker processes. Defaults to 4.",
            envvar="SCOUT_SCAN_MAX_PROCESSES",
        ),
        click.option(
            "--limit",
            type=int,
            help="Limit number of transcripts to scan.",
            envvar="SCOUT_SCAN_LIMIT",
        ),
        click.option(
            "--shuffle",
            is_flag=False,
            flag_value="true",
            default=None,
            callback=int_or_bool_flag_callback(-1),
            help="Shuffle order of transcripts (pass a seed to make the order deterministic)",
            envvar=["SCOUT_SCAN_SHUFFLE"],
        ),
        click.option(
            "--tags",
            type=str,
            help="Tags to associate with this scan job (comma separated)",
            envvar="SCOUT_SCAN_TAGS",
        ),
        click.option(
            "--metadata",
            multiple=True,
            type=str,
            help="Metadata to associate with this scan job (more than one --metadata argument can be specified).",
            envvar="SCOUT_SCAN_METADATA",
        ),
        click.option(
            "--cache",
            is_flag=False,
            flag_value="true",
            default=None,
            callback=int_bool_or_str_flag_callback(DEFAULT_CACHE_DAYS, None),
            help="Policy for caching of model generations. Specify --cache to cache with 7 day expiration (7D). Specify an explicit duration (e.g. (e.g. 1h, 3d, 6M) to set the expiration explicitly (durations can be expressed as s, m, h, D, W, M, or Y). Alternatively, pass the file path to a YAML or JSON config file with a full `CachePolicy` configuration.",
            envvar="SCOUT_SCAN_CACHE",
        ),
        click.option(
            "--batch",
            is_flag=False,
            flag_value="true",
            default=None,
            callback=int_bool_or_str_flag_callback(DEFAULT_BATCH_SIZE, None),
            help="Batch requests together to reduce API calls when using a model that supports batching (by default, no batching). Specify --batch to batch with default configuration, specify a batch size e.g. `--batch=1000` to configure batches of 1000 requests, or pass the file path to a YAML or JSON config file with batch configuration.",
            envvar="SCOUT_SCAN_BATCH",
        ),
        click.option(
            "--max-connections",
            type=int,
            help="Maximum number of concurrent connections to Model API (defaults to max_transcripts)",
            envvar="SCOUT_SCAN_MAX_CONNECTIONS",
        ),
        click.option(
            "--max-retries",
            type=int,
            help="Maximum number of times to retry model API requests (defaults to unlimited)",
            envvar="SCOUT_SCAN_MAX_RETRIES",
        ),
        click.option(
            "--timeout",
            type=int,
            help="Model API request timeout in seconds (defaults to no timeout)",
            envvar="SCOUT_SCAN_TIMEOUT",
        ),
        click.option(
            "--max-tokens",
            type=int,
            help="The maximum number of tokens that can be generated in the completion (default is model specific)",
            envvar="SCOUT_SCAN_MAX_TOKENS",
        ),
        click.option(
            "--temperature",
            type=float,
            help="What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.",
            envvar="SCOUT_SCAN_TEMPERATURE",
        ),
        click.option(
            "--top-p",
            type=float,
            help="An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass.",
            envvar="SCOUT_SCAN_TOP_P",
        ),
        click.option(
            "--top-k",
            type=int,
            help="Randomly sample the next word from the top_k most likely next words. Anthropic, Google, HuggingFace, and vLLM only.",
            envvar="SCOUT_SCAN_TOP_K",
        ),
        click.option(
            "--reasoning-effort",
            type=click.Choice(["minimal", "low", "medium", "high"]),
            help="Constrains effort on reasoning for reasoning models (defaults to `medium`). Open AI o-series and gpt-5 models only.",
            envvar="SCOUT_SCAN_REASONING_EFFORT",
        ),
        click.option(
            "--reasoning-tokens",
            type=int,
            help="Maximum number of tokens to use for reasoning. Anthropic Claude models only.",
            envvar="SCOUT_SCAN_REASONING_TOKENS",
        ),
        click.option(
            "--reasoning-summary",
            type=click.Choice(["concise", "detailed", "auto"]),
            help="Provide summary of reasoning steps (defaults to no summary). Use 'auto' to access the most detailed summarizer available for the current model. OpenAI reasoning models only.",
            envvar="SCOUT_SCAN_REASONING_SUMMARY",
        ),
        click.option(
            "--reasoning-history",
            type=click.Choice(["none", "all", "last", "auto"]),
            help='Include reasoning in chat message history sent to generate (defaults to "auto", which uses the recommended default for each provider)',
            envvar="SCOUT_SCAN_REASONING_HISTORY",
        ),
        click.option(
            "--debug",
            is_flag=True,
            envvar="SCOUT_DEBUG",
            help="Wait to attach debugger",
        ),
        click.option(
            "--debug-port",
            type=int,
            default=5678,
            envvar="SCOUT_DEBUG_PORT",
            help="Port number for debugger",
        ),
        click.option(
            "--fail-on-error",
            type=bool,
            is_flag=True,
            default=False,
            help="Re-raise exceptions instead of capturing them in results",
            envvar="SCOUT_SCAN_FAIL_ON_ERROR",
        ),
    ]
    for d in reversed(decorators):
        func = d(func)
    return func
