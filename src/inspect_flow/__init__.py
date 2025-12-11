"""inspect_flow methods for constructing flow configs."""

try:
    from ._version import __version__
except ImportError:  # pragma: no cover
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
    FlowModel,
    FlowOptions,
    FlowScorer,
    FlowSolver,
    FlowSpec,
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
    "FlowSpec",
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
