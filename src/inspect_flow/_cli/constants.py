from __future__ import annotations

from pathlib import Path
from types import ModuleType

import click
from inspect_ai._util.module import load_module

from inspect_flow._util.path_util import find_auto_includes


def _is_constant_name(name: str) -> bool:
    return bool(name) and not name.startswith("_") and name.isupper()


def _module_constants(module: ModuleType) -> dict[str, str]:
    return {
        name: value
        for name, value in vars(module).items()
        if _is_constant_name(name) and isinstance(value, str)
    }


def _discover_constants() -> dict[str, list[tuple[str, str]]]:
    result: dict[str, list[tuple[str, str]]] = {}
    for flow_file in find_auto_includes(str(Path.cwd())):
        module = load_module(Path(flow_file))
        if module is None:
            continue
        for name, value in _module_constants(module).items():
            result.setdefault(name, []).append((flow_file, value))
    return result


def _discover_constants_from_file(file_path: str) -> dict[str, str]:
    path = Path(file_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    if not path.exists():
        raise click.BadParameter(f"File not found: {file_path}")
    module = load_module(path)
    if module is None:
        return {}
    return _module_constants(module)


def _resolve_token(
    token: str,
    global_constants: dict[str, list[tuple[str, str]]] | None,
) -> str:
    if not token.startswith("@"):
        return token
    body = token[1:]
    if "@" in body:
        file_path, name = body.rsplit("@", 1)
        constants = _discover_constants_from_file(file_path)
        if name not in constants:
            raise click.BadParameter(f"Constant '{name}' not found in {file_path}.")
        return constants[name]
    if global_constants is None:
        global_constants = _discover_constants()
    entries = global_constants.get(body)
    if not entries:
        raise click.BadParameter(
            f"Constant '{body}' not found in any _flow.py. "
            f"Define it as an UPPERCASE module-level string."
        )
    values = {v for _, v in entries}
    if len(values) > 1:
        files = ", ".join(f for f, _ in entries)
        raise click.BadParameter(
            f"Constant '{body}' is defined in multiple files with "
            f"different values: {files}. Use file.py@{body} to disambiguate."
        )
    return entries[0][1]


def resolve_tokens(args: list[str]) -> list[str]:
    """Resolve @NAME and @file.py@NAME tokens in a list of CLI args.

    Tokens not starting with `@` are returned unchanged. Raises
    click.BadParameter on missing name or on collision (same name defined
    in multiple _flow.py files with different values).
    """
    needs_global = any(a.startswith("@") and "@" not in a[1:] for a in args)
    global_constants = _discover_constants() if needs_global else None
    return [_resolve_token(a, global_constants) for a in args]
