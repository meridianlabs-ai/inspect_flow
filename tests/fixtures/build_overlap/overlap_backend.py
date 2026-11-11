"""In-tree build backend that records the build requirement versions it sees."""

import importlib.metadata
import zipfile
from pathlib import Path

NAME = "overlap_pkg"
DIST_INFO = f"{NAME}-0.1.dist-info"
METADATA = "Metadata-Version: 2.1\nName: overlap-pkg\nVersion: 0.1\n"
WHEEL = "Wheel-Version: 1.0\nGenerator: overlap_backend\nRoot-Is-Purelib: true\nTag: py3-none-any\n"


def _record() -> None:
    seen = {p: importlib.metadata.version(p) for p in ("overlap-dep", "overlap-other")}
    (Path(__file__).parent / "build-saw.txt").write_text(repr(seen))


def prepare_metadata_for_build_editable(
    metadata_directory: str, config_settings: object = None
) -> str:
    _record()
    dist_info = Path(metadata_directory) / DIST_INFO
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(METADATA)
    return DIST_INFO


def build_editable(
    wheel_directory: str,
    config_settings: object = None,
    metadata_directory: str | None = None,
) -> str:
    _record()
    wheel = f"{NAME}-0.1-py3-none-any.whl"
    files = {
        f"{DIST_INFO}/METADATA": METADATA,
        f"{DIST_INFO}/WHEEL": WHEEL,
        f"{NAME}.pth": f"{Path(__file__).parent}\n",
    }
    record = "".join(f"{name},,\n" for name in [*files, f"{DIST_INFO}/RECORD"])
    with zipfile.ZipFile(Path(wheel_directory) / wheel, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
        z.writestr(f"{DIST_INFO}/RECORD", record)
    return wheel


def build_wheel(
    wheel_directory: str,
    config_settings: object = None,
    metadata_directory: str | None = None,
) -> str:
    return build_editable(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory: str, config_settings: object = None) -> str:
    raise NotImplementedError("test fixture builds wheels only")
