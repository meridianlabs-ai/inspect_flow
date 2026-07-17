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
    return _scanner_entries(scanner.scanners)


def _scanner_entries(scanners: Any) -> list[Any]:
    if scanners is None:
        return []
    if isinstance(scanners, dict):
        entries = list(scanners.values())
        if all(is_scanner_spec(e) or callable(e) for e in entries):
            return entries
        # anything else is a named key missing its value or a single spec
        # dict (e.g. a YAML mapping missing its list dash)
        raise ValueError(
            "ScannerConfig.scanners dict values must be scanners or scanner "
            "specs. If this was meant as a single scanner spec, wrap it in a "
            "list."
        )
    if isinstance(scanners, Sequence) and not isinstance(scanners, str):
        return list(scanners)
    # reject bare values: they aren't valid eval_set input, and a bare
    # ScannerSpec serializes to a dict indistinguishable from named scanners
    raise ValueError(
        "ScannerConfig.scanners must be a sequence of scanners or a dict of "
        f"named scanners, got {type(scanners).__name__}. "
        "Wrap a single scanner in a list."
    )


def _realize_entry(entry: Any) -> Any:
    if is_scanner_spec(entry):
        return _realize_scanner_specs([entry])[0]
    return entry


def resolve_scanner(scanner: str | ScannerConfig | None) -> ScannerConfig | None:
    if isinstance(scanner, str):
        return ScannerConfig.from_file(scanner)
    if not isinstance(scanner, ScannerConfig):
        return scanner
    # realize per-entry so configs mixing spec-form and live scanners work too
    scanners = scanner.scanners
    _scanner_entries(scanners)  # reject invalid shapes with a clear error
    if isinstance(scanners, dict):
        scanners = {k: _realize_entry(v) for k, v in scanners.items()}
    elif scanners is not None:
        scanners = [_realize_entry(entry) for entry in scanners]
    return scanner.model_copy(update={"scanners": scanners})
