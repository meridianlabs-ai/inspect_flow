from typing import Any

from inspect_ai import ScannerConfig
from inspect_ai._eval.task.scan import _realize_scanner_specs


def _scanner_entries(scanners: Any) -> list[Any]:
    if isinstance(scanners, dict):
        return list(scanners.values())
    if isinstance(scanners, list):
        return scanners
    return []


def has_live_scanners(scanner: str | ScannerConfig | None) -> bool:
    """Whether the scanner config holds live `Scanner` objects (vs. `ScannerSpec` dicts)."""
    if not isinstance(scanner, ScannerConfig):
        return False
    return any(
        not isinstance(entry, dict) for entry in _scanner_entries(scanner.scanners)
    )


def resolve_scanner(scanner: str | ScannerConfig | None) -> ScannerConfig | None:
    """Resolve a flow scanner option to a `ScannerConfig` ready for `eval_set()`."""
    if isinstance(scanner, str):
        return ScannerConfig.from_file(scanner)
    if isinstance(scanner, ScannerConfig) and not has_live_scanners(scanner):
        return scanner.model_copy(
            update={"scanners": _realize_scanner_specs(scanner.scanners)}
        )
    return scanner
