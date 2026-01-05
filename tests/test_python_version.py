from inspect_flow._launcher.python_version import (
    _all_versions_to_available_python_versions,
)
from packaging.version import Version


def test_to_available_versions():
    versions = _all_versions_to_available_python_versions(
        [
            "cpython-3.14.0rc3-macos-aarch64-none                 /Users/ransomrichardson/.local/share/uv/python/cpython-3.14.0rc3-macos-aarch64-none/bin/python3.14",
            "cpython-3.13.7+freethreaded-macos-aarch64-none       <download available>",
            "cpython-3.10.18-macos-aarch64-none                   /Users/ransomrichardson/.local/share/uv/python/cpython-3.10.18-macos-aarch64-none/bin/python3.10",
        ]
    )
    assert versions == [Version("3.13.7"), Version("3.10.18")]
