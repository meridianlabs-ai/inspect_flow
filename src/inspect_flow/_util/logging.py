from inspect_ai._util.logger import LogHandlerVar, init_logger

from inspect_flow._util.constants import PKG_NAME


def init_flow_logging(
    log_level: str | None,
    log_handler_var: LogHandlerVar | None = None,
) -> None:
    init_logger(
        log_level=log_level,
        env_prefix="INSPECT_FLOW",
        pkg_name=PKG_NAME,
        log_handler_var=log_handler_var,
    )
