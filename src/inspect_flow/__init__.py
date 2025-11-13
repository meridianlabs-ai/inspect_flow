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
    agent_merge,
    config_merge,
    model_merge,
    solver_merge,
    task_merge,
)

__all__ = [
    "__version__",
    "agent_merge",
    "agents_matrix",
    "agents_with",
    "config_merge",
    "configs_matrix",
    "configs_with",
    "flow_agent",
    "flow_config",
    "flow_model",
    "flow_solver",
    "flow_task",
    "model_merge",
    "models_matrix",
    "models_with",
    "solver_merge",
    "solvers_matrix",
    "solvers_with",
    "task_merge",
    "tasks_matrix",
    "tasks_with",
]
