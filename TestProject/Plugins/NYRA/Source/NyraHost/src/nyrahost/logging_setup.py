"""structlog JSON logging with 7-day TimedRotatingFileHandler (D-16).

Mounts a TimedRotatingFileHandler on the root logger rotating at midnight
with backupCount=7 so the Saved/NYRA/logs/ dir holds a week of daily
nyrahost-YYYY-MM-DD.log files, each being append-only JSON-per-line.

sys.excepthook is replaced with a structlog-aware handler so uncaught
exceptions surface as a single JSON log line (logger=nyrahost.crash,
event=uncaught_exception) with full traceback dict.
"""
from __future__ import annotations
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import structlog


def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"nyrahost-{datetime.now(timezone.utc):%Y-%m-%d}.log"
    handler = TimedRotatingFileHandler(
        log_file, when="midnight", backupCount=7, encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Uncaught exception hook -> log
    def excepthook(exc_type, exc_value, exc_tb):
        logger = structlog.get_logger("nyrahost.crash")
        logger.error(
            "uncaught_exception",
            error_type=exc_type.__name__,
            error_message=str(exc_value),
            exc_info=(exc_type, exc_value, exc_tb),
        )
    sys.excepthook = excepthook
