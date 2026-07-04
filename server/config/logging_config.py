"""
Logging Configuration for MultiUAV-Plat Server System

This module provides comprehensive logging configuration for the FastAPI server,
including request/response logging, error tracking, and command execution logging.

Each server run creates a new subdirectory with format: YYYYMMDDHHMMSS-<random_id>

Copyright (C) 2026 MultiUAV-Plat Server System Project
"""

import logging
import logging.handlers
import copy
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from config.util import generate_random_id


# Global variable to store current session directory
CURRENT_SESSION_DIR = None

# Base log directory
LOG_BASE_DIR = Path("server_logs")
LOG_BASE_DIR.mkdir(exist_ok=True)

# Log rotation settings
MAX_BYTES = 50 * 1024 * 1024  # 50 MB (increased for full bodies)
BACKUP_COUNT = 10  # Keep more backups


SENSITIVE_KEY_PARTS = ("key", "secret", "password", "token", "authorization")


def sanitize_sensitive_data(value: Any) -> Any:
    """Return a deep-copied value with sensitive dictionary fields redacted."""
    sanitized = copy.deepcopy(value)

    def mask(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested_value in item.items():
                key_text = str(key).lower()
                if any(part in key_text for part in SENSITIVE_KEY_PARTS):
                    if nested_value:
                        if isinstance(nested_value, list):
                            item[key] = [
                                "***REDACTED***" for _value in nested_value
                            ]
                        else:
                            item[key] = "***REDACTED***"
                else:
                    mask(nested_value)
        elif isinstance(item, list):
            for nested_value in item:
                mask(nested_value)

    mask(sanitized)
    return sanitized


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        return json.dumps(log_data, ensure_ascii=False)


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs"""

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log records"""
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            record.extra_data = sanitize_sensitive_data(record.extra_data)
        return True


def create_session_directory() -> Path:
    """Create a new session directory for this server run

    Returns:
        Path to the created session directory
    """
    # Generate session ID: YYYYMMDDHHMMSS-<random_id>
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_id = generate_random_id()
    session_id = f"{timestamp}-{random_id}"

    # Create session directory
    session_dir = LOG_BASE_DIR / session_id
    session_dir.mkdir(exist_ok=True)

    return session_dir


def get_session_log_path(filename: str) -> Path:
    """Get the full path for a log file in the current session directory

    Args:
        filename: Name of the log file (e.g., 'access.log')

    Returns:
        Full path to the log file
    """
    global CURRENT_SESSION_DIR
    if CURRENT_SESSION_DIR is None:
        raise RuntimeError("Logging not initialized. Call setup_logging() first.")
    return CURRENT_SESSION_DIR / filename


def setup_logging() -> Path:
    """Initialize logging configuration for the application

    Returns:
        Path to the session log directory
    """
    global CURRENT_SESSION_DIR

    # Create session directory
    CURRENT_SESSION_DIR = create_session_directory()

    # Define log file paths in session directory
    access_log_file = CURRENT_SESSION_DIR / "access.log"
    error_log_file = CURRENT_SESSION_DIR / "error.log"
    api_requests_log_file = CURRENT_SESSION_DIR / "api_requests.jsonl"  # JSONL format for structured logs
    commands_log_file = CURRENT_SESSION_DIR / "commands.log"

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Color codes for terminal output - FastAPI style
    class ColoredFormatter(logging.Formatter):
        """Custom formatter with colors for console output in FastAPI style"""

        # ANSI color codes
        COLORS = {
            'DEBUG': '\033[36m',      # Cyan
            'INFO': '\033[32m',       # Green
            'WARNING': '\033[33m',    # Yellow
            'ERROR': '\033[31m',      # Red
            'CRITICAL': '\033[35m',   # Magenta
        }
        RESET = '\033[0m'
        BOLD = '\033[1m'

        def format(self, record):
            # Create a copy of the record to avoid modifying the original
            # This prevents color codes from leaking into file handlers
            record_copy = logging.makeLogRecord(record.__dict__)

            # Add color to level name with colon (FastAPI style: "INFO:     ")
            # WARNING: is 8 chars, so pad to 10 total (level + colon + spaces)
            levelname = record_copy.levelname
            level_with_colon = f"{levelname}:"
            if levelname in self.COLORS:
                # Apply color, then pad the whole thing to 10 chars
                record_copy.levelname = f"{self.COLORS[levelname]}{level_with_colon:<10}{self.RESET}"
            else:
                record_copy.levelname = f"{level_with_colon:<10}"
            return super().format(record_copy)

    simple_formatter = ColoredFormatter(
        fmt="%(levelname)s%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    json_formatter = JSONFormatter()

    # Create sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    # Console handler (INFO level for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Access log handler (all HTTP requests)
    access_handler = logging.handlers.RotatingFileHandler(
        access_log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(detailed_formatter)
    access_handler.addFilter(sensitive_filter)

    # Error log handler (errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # API requests log handler (JSON format for data analysis)
    api_requests_handler = logging.handlers.RotatingFileHandler(
        api_requests_log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    api_requests_handler.setLevel(logging.INFO)
    api_requests_handler.setFormatter(json_formatter)
    api_requests_handler.addFilter(sensitive_filter)

    # Commands log handler (drone command execution)
    commands_handler = logging.handlers.RotatingFileHandler(
        commands_log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    commands_handler.setLevel(logging.INFO)
    commands_handler.setFormatter(detailed_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Configure app logger
    app_logger = logging.getLogger("uav_system")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(console_handler)
    app_logger.addHandler(access_handler)
    app_logger.addHandler(error_handler)

    # Configure API requests logger (structured JSON logging)
    api_logger = logging.getLogger("uav_system.api")
    api_logger.setLevel(logging.INFO)
    api_logger.addHandler(api_requests_handler)
    api_logger.propagate = False  # Don't propagate to parent logger

    # Configure commands logger
    commands_logger = logging.getLogger("uav_system.commands")
    commands_logger.setLevel(logging.INFO)
    commands_logger.addHandler(commands_handler)
    commands_logger.addHandler(console_handler)
    commands_logger.propagate = False

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # app_logger.info("="*80)
    # app_logger.info("Logging system initialized")
    app_logger.info(f"Session log directory: {CURRENT_SESSION_DIR.absolute()}")
    app_logger.info(f"Session ID: {CURRENT_SESSION_DIR.name}")
    # app_logger.info("="*80)

    return CURRENT_SESSION_DIR


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name

    Args:
        name: Logger name (e.g., 'uav_system.api', 'uav_system.commands')

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str,
    user_role: Optional[str] = None,
    request_body: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    error: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None,
    response_size_bytes: Optional[int] = None,
    response_body_type: str = "unknown",
    response_body_summary: str = "omitted",
) -> None:
    """Log API request with structured data for analysis

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: Request path
        status_code: HTTP status code
        duration_ms: Request processing duration in milliseconds
        client_ip: Client IP address
        user_role: User role (USER, SYSTEM, ADMIN)
        request_body: Request body data (for POST/PUT/DELETE)
        session_id: Current session ID
        error: Error message if request failed
        query_params: Query parameters from URL (e.g., ?data=True)
        response_size_bytes: Response size from Content-Length or captured body length
        response_body_type: Normalized response content type
        response_body_summary: Short reason full response body is omitted
    """
    logger = get_logger("uav_system.api")

    extra_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "client_ip": client_ip,
        "response_size_bytes": response_size_bytes,
        "response_body_type": response_body_type,
        "response_body_summary": response_body_summary,
    }

    if user_role:
        extra_data["user_role"] = user_role

    if session_id:
        extra_data["session_id"] = session_id

    # Include query parameters
    if query_params:
        extra_data["query_params"] = query_params

    # Include full request body - NO TRUNCATION
    if request_body is not None:
        extra_data["request_body"] = request_body

    if error:
        extra_data["error"] = error

    # Create log record with extra data
    log_record = logger.makeRecord(
        logger.name,
        logging.INFO if status_code < 400 else logging.ERROR,
        "(api_request)",
        0,
        f"{method} {path} {status_code} - {duration_ms:.2f}ms",
        (),
        None
    )
    log_record.extra_data = extra_data

    logger.handle(log_record)


def log_command_execution(
    drone_id: str,
    command: str,
    parameters: Dict[str, Any],
    result: str,
    session_id: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """Log drone command execution

    Args:
        drone_id: ID of the drone
        command: Command name
        parameters: Command parameters
        result: Execution result (SUCCESS, FAILED, etc.)
        session_id: Current session ID
        error: Error message if command failed
    """
    logger = get_logger("uav_system.commands")

    error_msg = f" | Error: {error}" if error else ""
    session_msg = f" | Session: {session_id}" if session_id else ""

    message = (
        f"COMMAND EXECUTED - Drone: {drone_id} | "
        f"Command: {command} | "
        f"Params: {parameters} | "
        f"Result: {result}"
        f"{session_msg}"
        f"{error_msg}"
    )

    if result.upper() in ["SUCCESS", "COMPLETED"]:
        logger.info(message)
    else:
        logger.error(message)


def get_current_session_dir() -> Optional[Path]:
    """Get the current session log directory

    Returns:
        Path to current session directory, or None if not initialized
    """
    return CURRENT_SESSION_DIR
