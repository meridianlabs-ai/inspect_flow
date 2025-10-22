from __future__ import annotations

from inspect_flow._types.flow_type_dicts import MatrixDict
from inspect_flow._types.flow_types import FlowConfig, Matrix, TaskConfig

matrix: MatrixDict = {"tasks": []}
matrix: MatrixDict = {}

config = FlowConfig({"matrix": [{"tasks": ["one_module/one_task"]}]})
config = FlowConfig({"matrix": [Matrix(tasks=[Matrix(tasks=[])])]})
config = FlowConfig({"matrix": [TaskConfig()]})
config = FlowConfig(matrix=[{"tasks": []}])
config = FlowConfig(matrix=[Matrix(tasks=[]), TaskConfig()])
config = FlowConfig(matrix=[Matrix(tasks=[{"name": "dict"}])])
config = FlowConfig(
    matrix=[Matrix(tasks=["string", TaskConfig(name="class"), {"name": "dict"}])]
)
config = FlowConfig(matrix=[Matrix(tasks=[])])
config = FlowConfig(bad=None)


def foo(config: FlowConfig) -> None:
    value = config.matrix[0].args
