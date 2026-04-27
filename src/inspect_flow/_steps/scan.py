import os
from logging import getLogger
from typing import Any, Literal, Sequence

import click
from inspect_ai._cli.util import (
    parse_cli_args,
    parse_cli_config,
    parse_model_role_cli_args,
)
from inspect_ai._util.config import resolve_args
from inspect_ai.log import EvalLog
from inspect_ai.model import BatchConfig, CachePolicy, GenerateConfig
from inspect_scout import (
    ScanJob,
    ScanJobConfig,
    Scanner,
    transcripts_from,
)
from inspect_scout import (
    scan as scout_scan,
)
from inspect_scout._cli.scan import _parse_validation
from inspect_scout._project import read_project
from inspect_scout._scanjob import (
    merge_project_into_scanjob,
    scanjob_from_cli_spec,
    scanjob_from_file,
)
from inspect_scout._scanner.scanner import scanners_from_file

from inspect_flow._steps._scan_options import scan_cli_options
from inspect_flow._steps.step import step
from inspect_flow._util.logging import get_last_log_level

logger = getLogger(__name__)


@step
@scan_cli_options
def scan(
    logs: list[EvalLog],
    scanners: (
        Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
        | dict[str, Scanner[Any]]
        | ScanJob
        | ScanJobConfig
        | str
        | None
    ) = None,
    s: tuple[str, ...] = (),
    scans: str | None = None,
    worklist: str | None = None,
    validation: tuple[str, ...] = (),
    model: str | None = None,
    model_base_url: str | None = None,
    m: tuple[str, ...] = (),
    model_config: str | None = None,
    model_role: tuple[str, ...] = (),
    max_transcripts: int | None = None,
    max_processes: int | None = None,
    limit: int | None = None,
    shuffle: int | None = None,
    tags: str | None = None,
    metadata: tuple[str, ...] = (),
    cache: int | str | None = None,
    batch: int | str | None = None,
    max_connections: int | None = None,
    max_retries: int | None = None,
    timeout: int | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None,
    reasoning_tokens: int | None = None,
    reasoning_summary: Literal["concise", "detailed", "auto"] | None = None,
    reasoning_history: Literal["none", "all", "last", "auto"] | None = None,
    debug: bool = False,
    debug_port: int = 5678,
    fail_on_error: bool = False,
) -> list[EvalLog]:
    """Run Inspect Scout scanners against the transcripts of eval logs.

    Mirrors the CLI surface of `scout scan`, minus `-T/--transcripts` (which
    flow sources from log paths) and `-F/--filter` (handled by flow's own
    `--filter`).

    Args:
        logs: EvalLog objects whose transcripts will be scanned.
        scanners: Scanners to run, as a sequence, dict, `ScanJob`,
            `ScanJobConfig`, or a path to a Python/YAML file containing
            scanjob/scanner definitions.
        s: One or more scanjob or scanner arguments (e.g. `-S arg=value`).
        scans: Location to write scan results to.
        worklist: Path to a JSON/YAML worklist file.
        validation: One or more validation set specifications.
        model: Default model for llm scanners.
        model_base_url: Base URL for the model API.
        m: Native model arguments (e.g. `-M arg=value`).
        model_config: YAML/JSON file with model arguments.
        model_role: Named model role with model name or YAML/JSON config.
        max_transcripts: Maximum number of transcripts to scan concurrently.
        max_processes: Number of worker processes.
        limit: Limit number of transcripts to scan.
        shuffle: Shuffle order of transcripts (pass a seed for determinism).
        tags: Comma-separated tags for the scan job.
        metadata: Metadata key=value pairs for the scan job.
        cache: Cache policy for model generations.
        batch: Batch configuration for model requests.
        max_connections: Maximum concurrent connections to the model API.
        max_retries: Maximum retries for model API requests.
        timeout: Model API request timeout in seconds.
        max_tokens: Maximum tokens for completions.
        temperature: Sampling temperature.
        top_p: Nucleus sampling parameter.
        top_k: Top-k sampling parameter.
        reasoning_effort: Reasoning effort level (OpenAI o-series, gpt-5).
        reasoning_tokens: Maximum reasoning tokens (Anthropic Claude).
        reasoning_summary: Reasoning summary style (OpenAI).
        reasoning_history: Reasoning history inclusion style.
        debug: Wait to attach a debugger before running.
        debug_port: Port number for the debugger.
        fail_on_error: Re-raise scanner exceptions instead of capturing them.

    Returns:
        The input EvalLog objects, unmodified.
    """
    if scanners is None:
        raise click.UsageError("scanners must be provided")

    if debug:
        import debugpy

        debugpy.listen(debug_port)
        click.echo("Waiting for debugger attach")
        debugpy.wait_for_client()
        click.echo("Debugger attached")

    os.environ["SCOUT_LOG_LEVEL"] = get_last_log_level().upper()

    scanjob_args = parse_cli_args(s)
    resolved_scanners: (
        Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
        | dict[str, Scanner[Any]]
        | ScanJob
        | ScanJobConfig
    )
    if isinstance(scanners, str):
        scanjob = scanjob_from_cli_spec(scanners, scanjob_args)
        if scanjob is None:
            scanjob = scanjob_from_file(scanners, scanjob_args)
        if scanjob is None:
            scanner_list = scanners_from_file(scanners, scanjob_args)
            if not scanner_list:
                raise click.UsageError(
                    f"No @scanjob or @scanner decorated functions found in '{scanners}'"
                )
            scanjob = ScanJob(transcripts=None, scanners=scanner_list)
        resolved_scanners = scanjob
    else:
        resolved_scanners = scanners

    if isinstance(resolved_scanners, ScanJob):
        merge_project_into_scanjob(read_project(), resolved_scanners)

    parsed_validation = _parse_validation(validation) if validation else None
    parsed_model_args = (
        parse_cli_config(m, model_config) if (m or model_config) else None
    )
    parsed_model_roles = parse_model_role_cli_args(model_role) if model_role else None

    cache_config: bool | CachePolicy | None
    if isinstance(cache, str):
        policy = CachePolicy.from_string(cache)
        cache_config = (
            policy
            if policy is not None
            else CachePolicy.model_validate(resolve_args(cache))
        )
    elif isinstance(cache, int):
        cache_config = CachePolicy(expiry=f"{cache}D")
    else:
        cache_config = cache

    batch_config: bool | int | BatchConfig | None
    if isinstance(batch, str):
        batch_config = BatchConfig.model_validate(resolve_args(batch))
    else:
        batch_config = batch

    generate_config = GenerateConfig(
        max_retries=max_retries,
        timeout=timeout,
        max_connections=max_connections,
        cache=cache_config,
        batch=batch_config,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        reasoning_effort=reasoning_effort,
        reasoning_tokens=reasoning_tokens,
        reasoning_summary=reasoning_summary,
        reasoning_history=reasoning_history,
    )

    scan_shuffle: bool | int | None
    if shuffle == -1:
        scan_shuffle = True
    elif shuffle == 0 or shuffle is None:
        scan_shuffle = None
    else:
        scan_shuffle = shuffle

    scout_scan(
        scanners=resolved_scanners,
        transcripts=transcripts_from([log.location for log in logs]),
        scans=scans,
        worklist=worklist,
        validation=parsed_validation,
        model=model,
        model_config=generate_config,
        model_base_url=model_base_url,
        model_args=parsed_model_args,
        model_roles=parsed_model_roles,
        max_transcripts=max_transcripts,
        max_processes=max_processes,
        limit=limit,
        shuffle=scan_shuffle,
        tags=tags.split(",") if tags else None,
        metadata=parse_cli_args(metadata) if metadata else None,
        fail_on_error=fail_on_error,
    )
    return logs
