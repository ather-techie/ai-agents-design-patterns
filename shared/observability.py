"""Structured logging and a small timing decorator.

Logs are emitted as one JSON object per line so they're greppable and
machine-parseable. ``get_logger`` returns a configured stdlib logger; ``@timed``
wraps a function and logs its duration. Logging is opt-in via the ``AGENT_LOG``
environment variable (e.g. ``AGENT_LOG=info``) so the demo's trace tree isn't
drowned out by log lines unless you ask for them.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """Render each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any structured fields passed via `extra={"fields": {...}}`.
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.environ.get("AGENT_LOG", "warning").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger("agent")
    root.handlers[:] = [handler]
    root.setLevel(getattr(logging, level_name, logging.WARNING))
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a structured logger under the ``agent`` namespace."""
    _configure_root()
    return logging.getLogger(f"agent.{name}")


def log(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    """Log ``message`` with arbitrary structured ``fields``."""
    logger.log(level, message, extra={"fields": fields})


def timed(func: F) -> F:
    """Decorator that logs the wrapped function's wall-clock duration."""
    logger = get_logger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            log(logger, logging.INFO, "call", func=func.__qualname__, ms=round(elapsed_ms, 2))

    return wrapper  # type: ignore[return-value]
