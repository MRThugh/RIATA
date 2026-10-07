"""
Configuration management for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.core.constants import (
    DEFAULT_LANGUAGE,
    LANG_AUTO,
    SUPPORTED_LANGUAGES,
)


def _parse_bool(val: Any, default: bool = False) -> bool:
    """Safely parse boolean values avoiding unsafe bool("false") evaluation."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("1", "true", "yes", "on"):
            return True
        if v in ("0", "false", "no", "off"):
            return False
    return default


@dataclass
class Config:
    language: str = LANG_AUTO
    theme: str = "dark"
    music_directory: str = field(default_factory=lambda: str(Path.home() / "Music"))
    dry_run: bool = False
    debug: bool = False
    logging_level: str = "INFO"
    safe_execution: bool = True

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file, env vars, and defaults."""
        data: dict[str, Any] = {}

        # Default paths to check
        candidates = []
        if config_path:
            candidates.append(config_path)
        candidates.extend([
            Path.cwd() / "config.json",
            Path.home() / ".config" / "riata" / "config.json",
        ])

        for path in candidates:
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data.update(loaded)
                    break
                except Exception:
                    pass

        # Environment variable overrides
        if "RIATA_DRY_RUN" in os.environ:
            data["dry_run"] = _parse_bool(os.environ["RIATA_DRY_RUN"], False)
        if "RIATA_DEBUG" in os.environ:
            data["debug"] = _parse_bool(os.environ["RIATA_DEBUG"], False)
            if data["debug"]:
                data["logging_level"] = "DEBUG"
        if os.getenv("RIATA_LANG") in SUPPORTED_LANGUAGES:
            data["language"] = os.environ["RIATA_LANG"]
        if os.getenv("RIATA_MUSIC_DIR"):
            data["music_directory"] = os.environ["RIATA_MUSIC_DIR"]
        if "RIATA_SAFE_EXECUTION" in os.environ:
            data["safe_execution"] = _parse_bool(os.environ["RIATA_SAFE_EXECUTION"], True)

        cfg = cls()
        if "language" in data and (data["language"] in SUPPORTED_LANGUAGES or data["language"] == LANG_AUTO):
            cfg.language = data["language"]
        if "theme" in data:
            cfg.theme = str(data["theme"])
        if "music_directory" in data:
            cfg.music_directory = str(data["music_directory"])
        if "dry_run" in data:
            cfg.dry_run = _parse_bool(data["dry_run"], cfg.dry_run)
        if "debug" in data:
            cfg.debug = _parse_bool(data["debug"], cfg.debug)
        if "logging_level" in data:
            cfg.logging_level = str(data["logging_level"])
        if "safe_execution" in data:
            cfg.safe_execution = _parse_bool(data["safe_execution"], cfg.safe_execution)

        return cfg


_GLOBAL_CONFIG: Optional[Config] = None


def get_config() -> Config:
    """Retrieve the global configuration instance."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = Config.load()
    return _GLOBAL_CONFIG


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = config
