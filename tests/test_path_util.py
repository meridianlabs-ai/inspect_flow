from pathlib import Path

from inspect_flow._util.path_util import find_file


def test_relative_path_resolution():
    path = Path(__file__)
    base_dir = path.parent
    file_name = path.name

    result = find_file(file_name, base_dir=base_dir)
    assert result == str(path.resolve())
