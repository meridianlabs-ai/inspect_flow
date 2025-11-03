try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from inspect_flow._submit.submit import submit
from inspect_flow._types.factories import (
    agents_matrix,
    configs_matrix,
    flow_agent,
    flow_config,
    flow_model,
    flow_solver,
    flow_task,
    models_matrix,
    solvers_matrix,
    tasks_matrix,
)

__all__ = [
    "__version__",
    "agents_matrix",
    "configs_matrix",
    "flow_agent",
    "flow_config",
    "flow_model",
    "flow_solver",
    "flow_task",
    "models_matrix",
    "solvers_matrix",
    "submit",
    "tasks_matrix",
]
