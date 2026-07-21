from collections.abc import Sequence
from typing import Any

from inspect_ai import ScannerConfig
from inspect_ai._eval.task.scan import _realize_scanner_specs
from inspect_scout import ScannerSpec


def is_scanner_spec(entry: Any) -> bool:
    return isinstance(entry, (dict, ScannerSpec))


def scanner_entries(scanner: str | ScannerConfig | None) -> list[Any]:
    if not isinstance(scanner, ScannerConfig):
        return []
    scanners = scanner.scanners
    if scanners is None:
        return []
    if isinstance(scanners, dict):
        return list(scanners.values())
    if isinstance(scanners, Sequence) and not isinstance(scanners, str):
        return list(scanners)
    return [scanners]


def resolve_scanner(scanner: str | ScannerConfig | None) -> ScannerConfig | None:
    if isinstance(scanner, str):
        return ScannerConfig.from_file(scanner)
    if not isinstance(scanner, ScannerConfig):
        return scanner
    # Realize only when every entry is a serialization-safe spec reference; any
    # other shape (live scanners, tuples, strings, mixed) passes through so
    # inspect_ai / scout owns its validation rather than us re-deriving it.
    entries = scanner_entries(scanner)
    if not (entries and all(is_scanner_spec(e) for e in entries)):
        return scanner
    scanners = scanner.scanners
    realized = _realize_scanner_specs(
        scanners if isinstance(scanners, dict) else entries
    )
    return scanner.model_copy(update={"scanners": realized})
