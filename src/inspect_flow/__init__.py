"""inspect_flow methods for constructing flow configs."""

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from inspect_flow._types.factories import (
    agents_matrix,
    agents_with,
    configs_matrix,
    configs_with,
    flow_agent,
    flow_config,
    flow_model,
    flow_solver,
    flow_task,
    models_matrix,
    models_with,
    solvers_matrix,
    solvers_with,
    tasks_matrix,
    tasks_with,
)
from inspect_flow._types.merge import (
    merge,
)

__all__ = [
    "__version__",
    "agents_matrix",
    "agents_with",
    "configs_matrix",
    "configs_with",
    "flow_agent",
    "flow_config",
    "flow_model",
    "flow_solver",
    "flow_task",
    "merge",
    "models_matrix",
    "models_with",
    "solvers_matrix",
    "solvers_with",
    "tasks_matrix",
    "tasks_with",
]
