"""Centralised logging configuration (console + rotating file) for the REMS app layer.

structlog is routed through the stdlib :mod:`logging` module so that every record — whether
emitted via ``structlog.get_logger()`` or by a third-party library — reaches both the console
handler (INFO) and the rotating file handler (DEBUG, ``logs/rems.log``).

This module is app-layer only: ``rems.core`` must stay import-safe with base deps and must never
import it (structlog is an app extra).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog
from structlog.typing import Processor

# src/rems/logging_config.py -> parents[2] == repo root
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "rems.log"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

_NOISY_LIBRARIES = ("httpx", "httpcore", "urllib3", "asyncio", "watchdog", "PIL")


def _shared_processors() -> list[Processor]:
    """Processors applied to both structlog and foreign (stdlib) records."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt=DATE_FORMAT),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]


def setup_logging(level: str = "INFO") -> None:
    """Initialise global logging: console (INFO) + rotating file (DEBUG). Idempotent.

    structlog is configured to emit through the stdlib handlers so the rotating file
    captures records from both structlog and third-party libraries. Console output is
    human-readable; the file is line-delimited JSON for later parsing.
    """
    LOG_DIR.mkdir(exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    if any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        return  # already configured

    shared = _shared_processors()
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
    )
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(console_formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    root.addHandler(file_handler)

    for library in _NOISY_LIBRARIES:
        logging.getLogger(library).setLevel(logging.WARNING)
