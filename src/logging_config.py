"""Centralized logging configuration for the Jalod Server API.

Provides a structured JSON formatter, a human-readable console formatter,
and helpers used across the application to obtain per-module loggers
and to bind a per-request correlation ID for tracing.
"""

import logging
import os
import sys
import uuid
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from typing import Optional

_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s] %(message)s"


class RequestIdFilter(logging.Filter):
    """Inject a per-request correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as compact JSON for ingestion by log aggregators."""

    DEFAULT_KEYS = {
        "asctime": "timestamp",
        "levelname": "level",
        "name": "logger",
        "message": "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName",
                "taskName", "request_id",
            ):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, default=str)


def configure_logging(app_name: str = "jalod_api") -> None:
    """Configure root logger and application logger.

    Reads the following environment variables:

    - ``LOG_LEVEL``: minimum level (default: ``INFO``).
    - ``LOG_FORMAT``: ``"json"`` or ``"console"`` (default: ``"console"``).
    - ``LOG_FILE``: optional path to a rotating file handler.
    """

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt_kind = os.environ.get("LOG_FORMAT", "console").lower()
    log_file = os.environ.get("LOG_FILE")

    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    if fmt_kind == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(_DEFAULT_FORMAT)

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(RequestIdFilter())
    root.addHandler(stream_handler)

    if log_file:
        directory = os.path.dirname(log_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIdFilter())
        root.addHandler(file_handler)

    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(level)

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.WARNING)

    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that inherits the application logging configuration."""
    return logging.getLogger(name)


def new_request_id() -> str:
    """Generate a fresh correlation ID for an incoming request."""
    return uuid.uuid4().hex


def set_request_id(request_id: str) -> None:
    """Bind a request ID to the current context for log correlation."""
    _request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Return the current request ID, or ``None`` if outside a request context."""
    return _request_id_var.get()
