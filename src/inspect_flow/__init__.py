"""inspect_flow methods for constructing flow configs."""

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from inspect_flow._types.decorator import after_load
from inspect_flow._types.factories import (
    agents_matrix,
    agents_with,
    configs_matrix,
    configs_with,
    models_matrix,
    models_with,
    solvers_matrix,
    solvers_with,
    tasks_matrix,
    tasks_with,
)
from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowDefaults,
    FlowDependencies,
    FlowEpochs,
    FlowJob,
    FlowModel,
    FlowOptions,
    FlowScorer,
    FlowSolver,
    FlowTask,
)
from inspect_flow._types.merge import (
    merge,
)

__all__ = [
    "__version__",
    "FlowAgent",
    "FlowDefaults",
    "FlowDependencies",
    "FlowEpochs",
    "FlowJob",
    "FlowModel",
    "FlowOptions",
    "FlowScorer",
    "FlowSolver",
    "FlowTask",
    "after_load",
    "agents_matrix",
    "agents_with",
    "configs_matrix",
    "configs_with",
    "merge",
    "models_matrix",
    "models_with",
    "solvers_matrix",
    "solvers_with",
    "tasks_matrix",
    "tasks_with",
]
