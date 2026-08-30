"""
Logging Infrastructure & UI Log Streamer (Standard Library Logging)
"""
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Callable, Optional
from app.config import LOGS_DIR

# Set up standard logger
log_file_path = LOGS_DIR / "ssr_bot.log"
std_logger = logging.getLogger("SSR_Bot")
std_logger.setLevel(logging.INFO)

# Avoid duplicate handlers on reload
if not std_logger.handlers:
    # Rotating file handler (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        filename=str(log_file_path),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
    file_handler.setFormatter(file_formatter)
    std_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(console_formatter)
    std_logger.addHandler(console_handler)


class UILoggerBridge:
    """Bridges application log events to the GUI log viewer and log file."""

    def __init__(self):
        self._callback: Optional[Callable[[str, str], None]] = None

    def set_callback(self, callback: Callable[[str, str], None]) -> None:
        self._callback = callback

    def log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level.upper()}] {message}"

        # Standard file logger
        lvl = level.upper()
        if lvl == "ERROR":
            std_logger.error(message)
        elif lvl == "WARNING":
            std_logger.warning(message)
        elif lvl == "SUCCESS" or lvl == "INFO":
            std_logger.info(message)
        elif lvl == "DEBUG":
            std_logger.debug(message)
        else:
            std_logger.info(message)

        # Dispatch to UI callback
        if self._callback:
            try:
                self._callback(level.upper(), formatted)
            except Exception:
                pass


ui_logger = UILoggerBridge()


def log_failure(
    *,
    category: str,
    process_name: str = "SSR Invoicing",
    step: str,
    record: str,
    error: str,
    retry_count: int = 0,
    status: str = "Failed",
) -> None:
    """Structured failure line for operators and support."""
    std_logger.error(
        "FAILURE | timestamp=%s | process=%s | step=%s | record=%s | "
        "category=%s | retry=%s | status=%s | error=%s",
        datetime.now().isoformat(timespec="seconds"),
        process_name,
        step or "-",
        record or "-",
        category,
        retry_count,
        status,
        error,
    )
