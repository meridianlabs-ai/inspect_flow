try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from inspect_flow._submit.submit import submit
from inspect_flow._types.factories import (
    configs,
    flow_agent,
    flow_config,
    flow_model,
    flow_solver,
    flow_task,
    models,
    solvers,
    tasks,
)

__all__ = [
    "__version__",
    "configs",
    "flow_agent",
    "flow_config",
    "flow_model",
    "flow_solver",
    "flow_task",
    "models",
    "solvers",
    "submit",
    "tasks",
]
