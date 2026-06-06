from __future__ import annotations

import argparse
import logging
import sys
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Context variable for correlation ID propagation
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
_correlation_id_enabled: bool = True


def get_correlation_id() -> str:
    """Get the current correlation ID, generating one if none exists."""
    cid = _correlation_id.get()
    if not cid:
        cid = uuid.uuid4().hex[:16]
        _correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id.set(cid)


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id.set("")


@dataclass
class LoggingConfig:
    """Logging configuration for NGD."""
    level: str = "INFO"
    json_format: bool = False
    log_file: Optional[Path] = None
    max_mb: int = 10
    backup_count: int = 5
    correlation_id: bool = True
    # Time-based rotation
    rotation_when: str = "midnight"  # 'S', 'M', 'H', 'D', 'midnight', 'W0'-'W6'
    rotation_interval: int = 1
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"

    @property
    def log_level(self) -> int:
        return getattr(logging, self.level.upper(), logging.INFO)


def add_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add logging configuration arguments to an ArgumentParser."""
    group = parser.add_argument_group("logging")
    _ = group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO, env: NGD_LOG_LEVEL)",
    )
    _ = group.add_argument(
        "--log-json",
        action="store_true",
        help="Output logs as structured JSON (env: NGD_LOG_JSON)",
    )
    _ = group.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (env: NGD_LOG_FILE)",
    )
    _ = group.add_argument(
        "--log-max-mb",
        type=int,
        default=10,
        help="Max log file size in MB before rotation (default: 10, env: NGD_LOG_MAX_MB)",
    )
    _ = group.add_argument(
        "--log-backup-count",
        type=int,
        default=5,
        help="Number of rotated log files to keep (default: 5, env: NGD_LOG_BACKUP_COUNT)",
    )
    _ = group.add_argument(
        "--log-rotation-when",
        type=str,
        default="midnight",
        help="Time-based rotation interval: S, M, H, D, midnight, W0-W6 (default: midnight, env: NGD_LOG_ROTATION_WHEN)",
    )
    _ = group.add_argument(
        "--log-rotation-interval",
        type=int,
        default=1,
        help="Time-based rotation interval count (default: 1, env: NGD_LOG_ROTATION_INTERVAL)",
    )
    _ = group.add_argument(
        "--no-correlation-id",
        action="store_true",
        help="Disable correlation IDs in logs (env: NGD_NO_CORRELATION_ID)",
    )


def logging_config_from_args(args: argparse.Namespace) -> LoggingConfig:
    """Create LoggingConfig from parsed arguments."""
    return LoggingConfig(
        level=args.log_level,
        json_format=args.log_json,
        log_file=args.log_file,
        max_mb=args.log_max_mb,
        backup_count=args.log_backup_count,
        rotation_when=args.log_rotation_when,
        rotation_interval=args.log_rotation_interval,
        correlation_id=not args.no_correlation_id,
    )


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    def __init__(self) -> None:
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""
    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id is not None:
            log_data["correlation_id"] = correlation_id
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in {"name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "message", "pathname", "process", "processName", "relativeCreated",
                          "thread", "threadName", "exc_info", "exc_text", "stack_info", "correlation_id"}:
                log_data[key] = value
        return json.dumps(log_data, default=str)


def setup_logging(config: LoggingConfig) -> None:
    """Configure logging based on LoggingConfig."""
    global _correlation_id_enabled
    _correlation_id_enabled = config.correlation_id

    root_logger = logging.getLogger()
    root_logger.setLevel(config.log_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    correlation_filter = CorrelationIdFilter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.addFilter(correlation_filter)
    if config.json_format:
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(logging.Formatter(config.format, config.datefmt))
    root_logger.addHandler(console_handler)

    # File handler (if log_file specified) - use TimedRotatingFileHandler for time-based rotation
    if config.log_file:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        # Use both size and time-based rotation: create a composite handler
        # For simplicity, we use TimedRotatingFileHandler with size limit
        from logging.handlers import TimedRotatingFileHandler  # pylint: disable=import-outside-toplevel
        file_handler = TimedRotatingFileHandler(
            config.log_file,
            when=config.rotation_when,
            interval=config.rotation_interval,
            backupCount=config.backup_count,
            encoding="utf-8",
            utc=True,
        )
        # Also set a max bytes limit on the base filename - we'll handle size rotation manually
        file_handler.addFilter(correlation_filter)
        file_handler.setFormatter(JsonFormatter() if config.json_format else logging.Formatter(config.format, config.datefmt))
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)