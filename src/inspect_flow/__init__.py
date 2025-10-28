try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from inspect_flow._types.flow_types import (
    FlowAgent,
    FlowConfig,
    FlowEpochs,
    FlowMatrix,
    FlowModel,
    FlowOptions,
    FlowSolver,
    FlowTask,
)

__all__ = [
    "__version__",
    "FlowAgent",
    "FlowConfig",
    "FlowEpochs",
    "FlowMatrix",
    "FlowModel",
    "FlowOptions",
    "FlowSolver",
    "FlowTask",
]
