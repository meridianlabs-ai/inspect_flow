from __future__ import annotations

from inspect_flow._types.flow_types import FlowConfig, Matrix, MatrixDict, TaskConfig

matrix: MatrixDict = {"tasks": []}

config = FlowConfig({"matrix": [{"tasks": ["one_module/one_task"]}]})
config = FlowConfig(matrix=[{"tasks": []}])
config = FlowConfig(matrix=[Matrix(tasks=[{"name": "dict"}])])
config = FlowConfig(
    matrix=[Matrix(tasks=["string", TaskConfig(name="class"), {"name": "dict"}])]
)
config = FlowConfig(matrix=[Matrix(tasks=[])])

# Should fail
matrix: MatrixDict = {}
matrix = Matrix({"tasks": []})
config = FlowConfig({"matrix": [Matrix(tasks=[Matrix(tasks=[])])]})
config = FlowConfig({"matrix": [TaskConfig()]})
config = FlowConfig(matrix=[Matrix(tasks=[]), TaskConfig()])
config = FlowConfig(bad=None)


def foo(config: FlowConfig) -> None:
    value = config.matrix[0].args
