import ast
import builtins
from functools import lru_cache
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType
from typing import Any

from inspect_ai._util.file import file

from inspect_flow._types.decorator import INSPECT_FLOW_AFTER_LOAD_ATTR


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
    g = {
        "__name__": "__main__",
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
    exec(code, g, g)
    if target_id is None:
        return None, g
    if not is_function_def:
        return g.get(target_id), g
    function = g.get(target_id)
    assert function and callable(function)
    if hasattr(function, INSPECT_FLOW_AFTER_LOAD_ATTR):
        return None, g
    return function(**args), g
