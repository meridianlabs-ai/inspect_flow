from typing import Any, Sequence

from inspect_ai.log import (
    EvalLog,
)
from inspect_scout import (
    ScanJob,
    ScanJobConfig,
    Scanner,
    transcripts_from,
)
from inspect_scout import (
    scan as scout_scan,
)

from inspect_flow._steps.step import step


@step
def scan(
    logs: list[EvalLog],
    scanners: (
        Sequence[Scanner[Any] | tuple[str, Scanner[Any]]]
        | dict[str, Scanner[Any]]
        | ScanJob
        | ScanJobConfig
    ),
) -> list[EvalLog]:
    """Run Inspect Scout scanners against the transcripts of eval logs.

    Args:
        logs: EvalLog objects whose transcripts will be scanned.
        scanners: Scanners to run, as a sequence, dict, `ScanJob`, or
            `ScanJobConfig`.

    Returns:
        The input EvalLog objects, unmodified.
    """
    # Scan all target logs in a single batch call
    scout_scan(
        scanners=scanners,
        transcripts=transcripts_from([log.location for log in logs]),
    )
    return logs
