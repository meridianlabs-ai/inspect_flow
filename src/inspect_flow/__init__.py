try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from inspect_flow._config.config import load_config
from inspect_flow._launcher.launch import launch
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
    "load_config",
    "models_matrix",
    "models_with",
    "solvers_matrix",
    "solvers_with",
    "launch",
    "tasks_matrix",
    "tasks_with",
]
