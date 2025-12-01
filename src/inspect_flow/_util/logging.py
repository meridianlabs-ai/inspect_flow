from inspect_ai._util.logger import init_logger

from inspect_flow._util.constants import PKG_NAME


def init_flow_logging(log_level: str | None) -> None:
    init_logger(log_level=log_level, env_prefix="INSPECT_FLOW", pkg_name=PKG_NAME)
