from typing import Any, Callable

from inspect_ai.log import (
    EvalLog,
)
from inspect_scout import (
    Scanner,
    Status,
    scan_results_df,
    transcripts_from,
)
from inspect_scout import (
    scan as scount_scan,
)
from pandas import DataFrame

from inspect_flow._steps.step import step

LogScanHandler = Callable[[EvalLog, Status, DataFrame], EvalLog]


@step
def scan(
    logs: list[EvalLog],
    handler: LogScanHandler,
    *,
    scanners: dict[str, Scanner[Any]],
    scans: str | None = None,
    model: str | None = None,
) -> list[EvalLog]:
    # Scan all target logs in a single batch call
    status = scount_scan(
        scans=scans,
        scanners=scanners,
        transcripts=transcripts_from([log.location for log in logs]),
        model=model,
    )

    scan_df = scan_results_df(status.location)
    for scanner_name in scanners.keys():
        df = scan_df.scanners[scanner_name]

    results: list[EvalLog] = []
    for log in target:
        # Filter scan results to this log's transcripts.
        # Normalize: strip file:// scheme for local paths, keep s3:// etc as-is.
        loc = UPath(log.location)
        log_uri = loc.resolve().path if loc.protocol in ("", "file") else str(loc)
        log_rows = df[df["transcript_source_uri"] == log_uri]
        # llm_scanner returns letter codes: "A" = first answer (NO_REFUSAL)
        refusal_count = (
            int((log_rows["value"] != "A").sum()) if not log_rows.empty else 0
        )
        scan_count = len(log_rows)
        has_refusal = refusal_count > 0
        has_errors = (
            log_rows["scan_error"].notna().any()
            if "scan_error" in log_rows.columns and not log_rows.empty
            else False
        )

        # Add scan details and location to metadata
        [log] = metadata(
            [log],
            set={
                "scans": status.location,
                "scan_complete": status.complete,
                "scan_errors": bool(has_errors),
                "scan_has_refusal": has_refusal,
            },
        )

        # Append summary to shared markdown report
        args_lines = (
            "\n".join(f"  - **{k}:** {v}" for k, v in log.eval.task_args.items())
            or "  - (none)"
        )
        section = f"""## {log.eval.model} — {log.eval.task}
- **Log:** `{log.location}`
- **Task args:**
{args_lines}
- **Refusals:** {refusal_count}/{scan_count} (`refusal_classifier`)
- **Scan:** `{status.location}`
- **Scan errors:** {int(has_errors)}
- **Result:** {"REFUSAL DETECTED" if has_refusal else "PASS"}

"""


...
