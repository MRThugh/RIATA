"""
Structured logging system for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import logging
import sys
from collections import deque
from typing import Callable, Optional

# In-memory buffer of recent log entries for diagnostics and UI
LOG_BUFFER: deque[str] = deque(maxlen=200)
_LOG_LISTENERS: list[Callable[[str], None]] = []


class BroadcastHandler(logging.Handler):
    """Custom logging handler that buffers and broadcasts logs to registered listeners."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            LOG_BUFFER.append(msg)
            for listener in _LOG_LISTENERS:
                try:
                    listener(msg)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def add_log_listener(listener: Callable[[str], None]) -> None:
    """Register a callback to receive real-time log records."""
    if listener not in _LOG_LISTENERS:
        _LOG_LISTENERS.append(listener)


def remove_log_listener(listener: Callable[[str], None]) -> None:
    """Unregister a log listener callback."""
    if listener in _LOG_LISTENERS:
        _LOG_LISTENERS.remove(listener)


def setup_logger(name: str = "riata", level: str = "INFO") -> logging.Logger:
    """Configure and return the structured application logger."""
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if setup is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="[%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    logger.addHandler(console_handler)

    broadcast_handler = BroadcastHandler()
    broadcast_handler.setFormatter(formatter)
    broadcast_handler.setLevel(numeric_level)
    logger.addHandler(broadcast_handler)

    return logger


def get_logger(name: str = "riata") -> logging.Logger:
    """Get the application logger."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        return setup_logger(name)
    return logger
