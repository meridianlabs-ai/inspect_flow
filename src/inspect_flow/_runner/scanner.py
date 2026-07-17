from collections.abc import Sequence
from typing import Any

from inspect_ai import ScannerConfig
from inspect_ai._eval.task.scan import _realize_scanner_specs
from inspect_scout import ScannerSpec


def _scanner_entries(scanners: Any) -> list[Any]:
    if scanners is None:
        return []
    if isinstance(scanners, dict):
        return list(scanners.values())
    if isinstance(scanners, Sequence) and not isinstance(scanners, str):
        return list(scanners)
    # reject bare values: they aren't valid eval_set input, and a bare
    # ScannerSpec serializes to a dict indistinguishable from named scanners
    raise ValueError(
        "ScannerConfig.scanners must be a sequence of scanners or a dict of "
        f"named scanners, got {type(scanners).__name__}. "
        "Wrap a single scanner in a list."
    )


def has_live_scanners(scanner: str | ScannerConfig | None) -> bool:
    if not isinstance(scanner, ScannerConfig):
        return False
    return any(
        not isinstance(entry, (dict, ScannerSpec))
        for entry in _scanner_entries(scanner.scanners)
    )


def _realize_entry(entry: Any) -> Any:
    if isinstance(entry, (dict, ScannerSpec)):
        return _realize_scanner_specs([entry])[0]
    return entry


def resolve_scanner(scanner: str | ScannerConfig | None) -> ScannerConfig | None:
    if isinstance(scanner, str):
        return ScannerConfig.from_file(scanner)
    if not isinstance(scanner, ScannerConfig):
        return scanner
    # realize per-entry so configs mixing spec-form and live scanners work too
    scanners = scanner.scanners
    if isinstance(scanners, dict):
        scanners = {k: _realize_entry(v) for k, v in scanners.items()}
    elif scanners is not None:
        scanners = [_realize_entry(entry) for entry in _scanner_entries(scanners)]
    return scanner.model_copy(update={"scanners": scanners})
