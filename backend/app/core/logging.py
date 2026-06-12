"""Structured JSON logging for activia-trace.

Replaces the root logger's handler with a JSON formatter that emits
one line per event.  Fields: timestamp, level, message, plus any
extras passed to ``extra=``.

Usage:
    from app.core.logging import setup_logging
    setup_logging()

    import logging
    logger = logging.getLogger(__name__)
    logger.info("hello", extra={"key": "value"})
"""

import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Merge any extras (never include PII / secrets)
        extras = {k: v for k, v in record.__dict__.items()
                  if k not in ("timestamp", "level", "message",
                               "module", "function", "line",
                               "args", "msg", "exc_info", "exc_text",
                               "stack_info", "name", "pathname",
                               "lineno", "funcName", "created",
                               "msecs", "relativeCreated",
                               "process", "thread", "threadName")}
        if extras:
            payload["extras"] = extras

        if record.exc_info and record.exc_info[0]:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure the root logger with the JSON formatter."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Quiet noisy libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
