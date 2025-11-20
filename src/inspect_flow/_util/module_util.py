import ast
import builtins
from functools import lru_cache
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from types import ModuleType

from inspect_ai._util.file import file

from inspect_flow._types.flow_types import FlowJob


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
    path: str, flow_vars: dict[str, str], including_jobs: list[FlowJob] | None
) -> object | None:
    with file(path, "r", encoding="utf-8") as f:
        src = f.read()
    mod = ast.parse(src, filename=path, mode="exec")
    if not mod.body:
        return None

    *prefix, last = mod.body
    target_id = "_"
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
    else:
        return None
    # else: leave as-is; result will be None

    code = compile(ast.fix_missing_locations(mod), path, "exec")
    g = {
        "__name__": "__main__",
        "__builtins__": builtins.__dict__,
        "__flow_vars__": flow_vars,
        "__flow_including_jobs__": including_jobs or [],
    }
    exec(code, g, g)
    return g.get(target_id)
