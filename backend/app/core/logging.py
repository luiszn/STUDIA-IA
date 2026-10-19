"""Structured logging configuration for the API."""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

_CONFIGURED = False

_LEVEL_STYLES = {
    "DEBUG": "\033[90m",
    "INFO": "\033[36m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[1;41m",
}
_RESET = "\033[0m"


class _Formatter(logging.Formatter):
    def __init__(self, colorize: bool) -> None:
        super().__init__()
        self._colorize = colorize

    def format(self, record: logging.LogRecord) -> str:
        name = record.name.replace("app.", "")
        timestamp = self.formatTime(record)
        base = f"{timestamp} {record.levelname:<8} {name:<22} {record.getMessage()}"
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        if self._colorize:
            style = _LEVEL_STYLES.get(record.levelname, "")
            return f"{style}{base}{_RESET}"
        return base


def configure_logging() -> None:
    """Idempotent root logger setup."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_Formatter(colorize=not settings.is_production and sys.stdout.isatty()))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Keep third party chatter down.
    for noisy in ("uvicorn.access", "httpx", "httpcore", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)