from logging import getLogger
from typing import Any, Literal, Sequence

import click
import yaml
from inspect_ai._cli.util import (
    parse_cli_args,
    parse_cli_config,
    parse_model_role_cli_args,
)
from inspect_ai._util.config import resolve_args
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import (
    absolute_file_path,
    dirname,
    file,
    filesystem,
    local_path,
)
from inspect_ai.log import EvalLog
from inspect_ai.model import BatchConfig, CachePolicy, GenerateConfig
from inspect_scout import (
    ScanJob,
    ScanJobConfig,
    Scanner,
    Status,
    transcripts_from,
)
from inspect_scout import (
    scan as scout_scan,
)
from inspect_scout._project import read_project
from inspect_scout._scanjob import (
    merge_project_into_scanjob,
    scanjob_from_cli_spec,
    scanjob_from_file,
)
from inspect_scout._scanner.scanner import scanners_from_file

from inspect_flow._display.display import get_display_type
from inspect_flow._steps.context import _step_context_var
from inspect_flow._steps.scan_options import scan_cli_options
from inspect_flow._steps.step import step
from inspect_flow._util.logging import get_last_log_level
from inspect_flow._util.path_util import path_join

logger = getLogger(__name__)


ScannersSpec = (
    Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
    | dict[str, Scanner[Any]]
    | ScanJob
    | ScanJobConfig
    | str
)


def _canonical_path(path: str) -> str:
    """Canonical form for scout.yaml path values.

    Local paths are returned as absolute paths without a file:// prefix; remote
    paths (s3://, etc.) are returned unchanged. Keeps the two keys in scout.yaml
    in a single consistent form.
    """
    return absolute_file_path(local_path(path))


def _write_scout_project_file(*, scans: str, transcripts: str) -> None:
    parent = dirname(scans)
    project_path = path_join(parent, "scout.yaml") if parent else "scout.yaml"
    if filesystem(project_path).exists(project_path):
        logger.info(
            "scout project file already exists at %s; leaving it unchanged",
            project_path,
        )
        return
    with file(project_path, "w") as f:
        f.write(yaml.safe_dump({"transcripts": transcripts, "scans": scans}))


def scan(
    logs: list[EvalLog],
    scanners: ScannersSpec,
    s: tuple[str, ...] = (),
    scans: str | None = None,
    validation: tuple[str, ...] = (),
    model: str | None = None,
    model_base_url: str | None = None,
    m: tuple[str, ...] = (),
    model_config: str | None = None,
    model_role: tuple[str, ...] = (),
    max_transcripts: int | None = None,
    max_processes: int | None = None,
    limit: int | None = None,
    shuffle: int = 0,
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
    fail_on_error: bool = False,
    dry_run: bool = False,
) -> Status:
    """Run Inspect Scout scanners against the transcripts of eval logs.

    Mirrors the CLI surface of `scout scan`, minus `-T/--transcripts` (which
    flow sources from log paths) and `-F/--filter` (handled by flow's own
    `--filter`). Returns scout's `Status`. For use as a flow step (logs only),
    see `scan_step`.

    Args:
        logs: EvalLog objects whose transcripts will be scanned.
        scanners: Scanners to run, as a sequence, dict, `ScanJob`,
            `ScanJobConfig`, or a path to a Python/YAML file containing
            scanjob/scanner definitions.
        s: One or more scanjob or scanner arguments (e.g. `-S arg=value`).
        scans: Location to write scan results to.
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
        fail_on_error: Re-raise scanner exceptions instead of capturing them.
        dry_run: Print resolved scanners and transcript counts without scanning.

    Returns:
        Scout's `Status` describing the completed scan.
    """
    flow_display = get_display_type()
    scout_display: Literal["rich", "plain", "log", "none"] = (
        "rich" if flow_display in ("full", "conversation") else flow_display
    )

    scanjob_args = parse_cli_args(s)
    resolved_scanners: ScannersSpec
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

    log_dirs = {dirname(log.location) for log in logs}

    if len(log_dirs) > 1:
        if scans is None:
            raise ValueError(
                "Cannot infer scans location: input logs are in multiple "
                "directories. Specify scans explicitly."
            )
    elif len(log_dirs) == 1:
        log_dir = _canonical_path(next(iter(log_dirs)))
        scans = _canonical_path(scans) if scans else path_join(log_dir, "scans")
        _write_scout_project_file(scans=scans, transcripts=log_dir)

    if validation:
        # Deferred: importing inspect_scout._cli pulls in inspect_ai._cli internals
        # that can break when scout and inspect-ai versions are out of sync (e.g.
        # scout <= 0.4.44 with inspect-ai >= 0.3.248), which would make all of
        # inspect_flow.api unimportable if done at module level.
        try:
            from inspect_scout._cli.scan import _parse_validation
        except ImportError as ex:
            raise PrerequisiteError(
                "validation requires importing inspect_scout._cli, which failed. "
                "This usually means the installed inspect-scout is incompatible "
                "with the installed inspect-ai; upgrade inspect-scout."
            ) from ex

        parsed_validation = _parse_validation(validation)
    else:
        parsed_validation = None
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
    elif shuffle == 0:
        scan_shuffle = None
    else:
        scan_shuffle = shuffle

    return scout_scan(
        scanners=resolved_scanners,
        transcripts=transcripts_from([log.location for log in logs]),
        scans=scans,
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
        display=scout_display,
        log_level=get_last_log_level(),
        fail_on_error=fail_on_error,
        dry_run=dry_run,
    )


@step
@scan_cli_options
def scan_step(
    logs: list[EvalLog],
    scanners: ScannersSpec,
    s: tuple[str, ...] = (),
    scans: str | None = None,
    validation: tuple[str, ...] = (),
    model: str | None = None,
    model_base_url: str | None = None,
    m: tuple[str, ...] = (),
    model_config: str | None = None,
    model_role: tuple[str, ...] = (),
    max_transcripts: int | None = None,
    max_processes: int | None = None,
    limit: int | None = None,
    shuffle: int = 0,
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
    fail_on_error: bool = False,
) -> list[EvalLog]:
    """Run Inspect Scout scanners against the transcripts of eval logs.

    Mirrors the CLI surface of `scout scan`, minus `-T/--transcripts` (which
    flow sources from log paths) and `-F/--filter` (handled by flow's own
    `--filter`). For programmatic callers needing scout's `Status` return
    value, use `scan`.

    Args:
        logs: EvalLog objects whose transcripts will be scanned.
        scanners: Scanners to run, as a sequence, dict, `ScanJob`,
            `ScanJobConfig`, or a path to a Python/YAML file containing
            scanjob/scanner definitions.
        s: One or more scanjob or scanner arguments (e.g. `-S arg=value`).
        scans: Location to write scan results to.
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
        fail_on_error: Re-raise scanner exceptions instead of capturing them.

    Returns:
        The input EvalLog objects, unmodified.
    """
    scan(
        logs,
        scanners=scanners,
        s=s,
        scans=scans,
        validation=validation,
        model=model,
        model_base_url=model_base_url,
        m=m,
        model_config=model_config,
        model_role=model_role,
        max_transcripts=max_transcripts,
        max_processes=max_processes,
        limit=limit,
        shuffle=shuffle,
        tags=tags,
        metadata=metadata,
        cache=cache,
        batch=batch,
        max_connections=max_connections,
        max_retries=max_retries,
        timeout=timeout,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        reasoning_effort=reasoning_effort,
        reasoning_tokens=reasoning_tokens,
        reasoning_summary=reasoning_summary,
        reasoning_history=reasoning_history,
        fail_on_error=fail_on_error,
        dry_run=(ctx := _step_context_var.get()) is not None and ctx.dry_run,
    )
    return logs
