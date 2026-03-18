from logging import Logger, LoggerAdapter, getLevelName, getLogger
from typing import Any, MutableMapping

from inspect_ai._util.constants import TRACE
from inspect_ai._util.logger import LogHandlerVar, _logHandler, init_logger

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


def update_log_level(log_level: str) -> None:
    handler = _logHandler["handler"]
    if handler is not None:
        level = getLevelName(log_level.upper())
        capture_level = min(TRACE, level)
        handler.display_level = level
        handler.setLevel(capture_level)
        getLogger().setLevel(level)
        for pkg in (PKG_NAME, "inspect_ai"):
            getLogger(pkg).setLevel(capture_level)


class PrefixLogger(LoggerAdapter):
    def __init__(self, logger: Logger, prefix: str) -> None:
        super().__init__(logger, {})
        self.prefix = prefix

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        return f"[{self.prefix}] {msg}", kwargs
