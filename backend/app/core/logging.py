"""
core/logging.py — Structured JSON logging for activia-trace.

Replaces the root logger's formatter with a JSON formatter that emits
one line per log event with fields: timestamp, level, message, plus any
extras passed via `extra={}` on the log call.

IMPORTANT: logs NEVER contain secrets or PII in plain text.

Implemented: C-01 (foundation-setup)
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class _JsonFormatter(logging.Formatter):
    """Format each log record as a single-line JSON string."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        log_entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra fields injected via `extra={}` — skip internal attrs
        _std_attrs = logging.LogRecord.__dict__.keys() | {
            "args",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
        }
        for key, val in record.__dict__.items():
            if key not in _std_attrs:
                log_entry[key] = val

        # Attach exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger to emit structured JSON to stdout.

    Call this once during app startup (before the first log message).
    Subsequent calls are idempotent: they update the level but do not
    add duplicate handlers.

    Args:
        level: root log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Remove any pre-existing handlers to avoid duplicate output
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
