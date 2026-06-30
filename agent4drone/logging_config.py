import logging
import os
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5

_CONFIGURED = False
ACTIVE_LOG_FILE: Path | None = None


def _entrypoint_name() -> str:
    script_name = Path(sys.argv[0]).stem or "interactive"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", script_name).strip("._-")
    return safe_name or "interactive"


def _new_log_file() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"agent4drone_{_entrypoint_name()}_{timestamp}_{os.getpid()}.log"


def configure_logging() -> None:
    """Configure project-wide operational logging."""
    global _CONFIGURED, ACTIVE_LOG_FILE
    if _CONFIGURED:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_LOG_FILE = _new_log_file()

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = RotatingFileHandler(
        ACTIVE_LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(isinstance(handler, RotatingFileHandler) for handler in root_logger.handlers):
        root_logger.addHandler(file_handler)
    if not any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
        for handler in root_logger.handlers
    ):
        root_logger.addHandler(stream_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


def get_active_log_file() -> Path | None:
    return ACTIVE_LOG_FILE
