import ast
import builtins
import runpy
from functools import lru_cache
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType


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


def execute_file_and_get_last_result(path: Path) -> object | None:
    src = open(path, "r", encoding="utf-8").read()
    mod = ast.parse(src, filename=path, mode="exec")
    if not mod.body:
        return None

    *prefix, last = mod.body
    if isinstance(last, ast.Expr):
        # rewrite final expression:  _ = <expr>
        last = ast.Assign(targets=[ast.Name(id="_", ctx=ast.Store())], value=last.value)
        mod = ast.Module(body=[*prefix, last], type_ignores=[])
    elif isinstance(last, ast.Assign):
        # rewrite final assignment to use name "_"
        last.targets = [ast.Name(id="_", ctx=ast.Store())]
        mod = ast.Module(body=[*prefix, last], type_ignores=[])
    else:
        return None
    # else: leave as-is; result will be None

    code = compile(ast.fix_missing_locations(mod), path, "exec")
    g = {"__name__": "__main__", "__builtins__": builtins.__dict__}
    exec(code, g, g)
    return g.get("_")
