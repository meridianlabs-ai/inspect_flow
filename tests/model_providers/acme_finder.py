import json
import sys
from importlib.machinery import ModuleSpec, PathFinder, all_suffixes
from importlib.util import spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Sequence

MAPPING: dict[str, str] = json.loads(Path(__file__).with_suffix(".json").read_text())
install_calls = 0


class _EditableFinder:
    @classmethod
    def find_spec(
        cls,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        if fullname in MAPPING:
            root = Path(MAPPING[fullname])
            candidates = [root / "__init__.py"] + [
                root.with_suffix(suffix) for suffix in all_suffixes()
            ]
            for candidate in candidates:
                if candidate.exists():
                    return spec_from_file_location(fullname, candidate)
        parent, _, _ = fullname.rpartition(".")
        if parent in MAPPING:
            return PathFinder.find_spec(fullname, path=[MAPPING[parent]])
        return None


def install() -> None:
    global install_calls
    install_calls += 1
    if _EditableFinder not in sys.meta_path:
        sys.meta_path.append(_EditableFinder)
