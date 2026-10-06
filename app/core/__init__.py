"""Core package for R.I.A.T.A."""

from app.core.constants import __version__, APP_NAME, APP_FULL_NAME, APP_AUTHOR
from app.core.config import Config, get_config
from app.core.logger import setup_logger, get_logger

__all__ = [
    "__version__",
    "APP_NAME",
    "APP_FULL_NAME",
    "APP_AUTHOR",
    "Config",
    "get_config",
    "setup_logger",
    "get_logger",
]
