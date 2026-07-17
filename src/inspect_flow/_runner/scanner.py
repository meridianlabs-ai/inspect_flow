from collections.abc import Sequence
from typing import Any

from inspect_ai import ScannerConfig
from inspect_ai._eval.task.scan import _realize_scanner_specs
from inspect_scout import ScannerSpec


def _scanner_entries(scanners: Any) -> list[Any]:
    if isinstance(scanners, dict):
        return list(scanners.values())
    if isinstance(scanners, Sequence) and not isinstance(scanners, str):
        return list(scanners)
    return [] if scanners is None else [scanners]


def has_live_scanners(scanner: str | ScannerConfig | None) -> bool:
    if not isinstance(scanner, ScannerConfig):
        return False
    return any(
        not isinstance(entry, (dict, ScannerSpec))
        for entry in _scanner_entries(scanner.scanners)
    )


def resolve_scanner(scanner: str | ScannerConfig | None) -> ScannerConfig | None:
    if isinstance(scanner, str):
        return ScannerConfig.from_file(scanner)
    if isinstance(scanner, ScannerConfig) and not has_live_scanners(scanner):
        # _realize_scanner_specs only handles list/dict, so normalize other
        # sequences (e.g. tuples) to a list
        scanners = scanner.scanners
        if isinstance(scanners, Sequence) and not isinstance(scanners, str):
            scanners = list(scanners)
        return scanner.model_copy(update={"scanners": _realize_scanner_specs(scanners)})
    return scanner
