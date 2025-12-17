from inspect_ai._util.logger import LogHandlerVar, init_logger

from inspect_flow._util.constants import DEFAULT_LOG_LEVEL, PKG_NAME

_last_log_level = DEFAULT_LOG_LEVEL


def init_flow_logging(
    log_level: str,
    log_handler_var: LogHandlerVar | None = None,
) -> None:
    global _last_log_level
    _last_log_level = log_level
    init_logger(
        log_level=log_level,
        env_prefix="INSPECT_FLOW",
        pkg_name=PKG_NAME,
        log_handler_var=log_handler_var,
    )


def get_last_log_level() -> str:
    return _last_log_level
