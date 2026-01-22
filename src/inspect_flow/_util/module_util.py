import ast
import builtins
import sys
from contextvars import ContextVar
from functools import lru_cache
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType
from typing import Any

from inspect_ai._util.file import file, filesystem

from inspect_flow._types.decorator import INSPECT_FLOW_AFTER_LOAD_ATTR

_loading_spec: ContextVar[bool] = ContextVar("_loading_spec", default=False)


def is_loading_spec() -> bool:
    """Check if we're currently loading a spec file."""
    return _loading_spec.get()


@lru_cache(maxsize=None)
def get_module_from_file(file: str) -> ModuleType:
    module_path = Path(file).resolve()
    module_name = module_path.as_posix()
    loader = SourceFileLoader(module_name, module_path.absolute().as_posix())
    spec = spec_from_loader(loader.name, loader)
    if not spec:
        raise ModuleNotFoundError(f"Module {module_name} not found")
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


def execute_file_and_get_last_result(
    path: str, args: dict[str, Any]
) -> tuple[object | None, dict[str, Any]]:
    with file(path, "r", encoding="utf-8") as f:
        src = f.read()
    return execute_src_and_get_last_result(src, path, args)


def execute_src_and_get_last_result(
    src: str,
    filename: str,
    args: dict[str, Any],
) -> tuple[object | None, dict[str, Any]]:
    # For local files, add the parent directory to sys.path to enable imports
    file_dir: str | None = None
    if filesystem(filename).is_local():
        file_dir = str(Path(filename).resolve().parent)
        if file_dir not in sys.path:
            sys.path.insert(0, file_dir)
        else:
            file_dir = None  # Don't remove it later if it was already there

    g = {
        "__name__": "__flow__",
        "__builtins__": builtins.__dict__,
        "__file__": filename,
    }
    mod = ast.parse(src, filename=filename, mode="exec")
    if not mod.body:
        return None, g

    *prefix, last = mod.body
    target_id = "_"
    is_function_def = False
    if isinstance(last, ast.Expr):
        # rewrite final expression:  _ = <expr>
        last = ast.Assign(
            targets=[ast.Name(id=target_id, ctx=ast.Store())], value=last.value
        )
        mod = ast.Module(body=[*prefix, last], type_ignores=[])
    elif isinstance(last, ast.Assign):
        target_ids = [t.id for t in last.targets if isinstance(t, ast.Name)]
        if len(target_ids) != 1:
            raise ValueError(
                "Only single target assignments are supported in config files"
            )
        target_id = target_ids[0]
    elif isinstance(last, ast.FunctionDef):
        # If the last statement is a function definition, use its name as the target
        target_id = last.name
        is_function_def = True
    else:
        target_id = None
    # else: leave as-is; result will be None

    code = compile(ast.fix_missing_locations(mod), filename=filename, mode="exec")
    token = _loading_spec.set(True)
    try:
        exec(code, g, g)
    finally:
        _loading_spec.reset(token)
        if file_dir is not None:
            sys.path.remove(file_dir)
    if target_id is None:
        return None, g
    if not is_function_def:
        return g.get(target_id), g
    function = g.get(target_id)
    assert function and callable(function)
    if hasattr(function, INSPECT_FLOW_AFTER_LOAD_ATTR):
        return None, g
    return function(**args), g
