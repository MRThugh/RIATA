"""
Language pack loader for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.core.constants import LANG_ENGLISH, LANG_PERSIAN
from app.core.logger import get_logger

logger = get_logger("riata.languages")


@dataclass
class LanguagePack:
    code: str
    name: str
    english_name: str
    direction: str  # 'rtl' or 'ltr'
    version: str
    responses: dict[str, str] = field(default_factory=dict)
    intents: dict[str, Any] = field(default_factory=dict)
    normalization: dict[str, Any] = field(default_factory=dict)

    def get_response(self, key: str, default: str = "", **kwargs: Any) -> str:
        """Format a response string using keyword parameters safely."""
        template = self.responses.get(key, default)
        if not template:
            return default
        try:
            return template.format(**kwargs)
        except KeyError as err:
            logger.warning("Missing format key %s in response %s", err, key)
            return template


class LanguageLoader:
    """Discovers and loads all language packs dynamically from directory."""

    def __init__(self, languages_dir: Optional[Path] = None) -> None:
        if languages_dir is None:
            # Look relative to workspace root or app directory
            candidates = [
                Path.cwd() / "languages",
                Path(__file__).resolve().parent.parent.parent / "languages",
            ]
            for candidate in candidates:
                if candidate.is_dir():
                    languages_dir = candidate
                    break
            if languages_dir is None:
                languages_dir = Path.cwd() / "languages"

        self.languages_dir = languages_dir
        self._packs: dict[str, LanguagePack] = {}
        self.load_all()

    def load_all(self) -> None:
        """Scan directory and load all language subfolders."""
        self._packs.clear()
        if not self.languages_dir.exists():
            logger.error("Languages directory does not exist: %s", self.languages_dir)
            return

        for item in self.languages_dir.iterdir():
            if item.is_dir():
                pack = self._load_single_pack(item)
                if pack:
                    self._packs[pack.code] = pack
                    logger.debug("Loaded language pack: %s (%s)", pack.code, pack.name)

    def _load_single_pack(self, pack_dir: Path) -> Optional[LanguagePack]:
        """Load language.json, intents.json, and normalization.json from folder."""
        lang_file = pack_dir / "language.json"
        if not lang_file.is_file():
            return None

        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                lang_meta = json.load(f)

            intents_file = pack_dir / "intents.json"
            intents_data: dict[str, Any] = {}
            if intents_file.is_file():
                with open(intents_file, "r", encoding="utf-8") as f:
                    intents_json = json.load(f)
                    intents_data = intents_json.get("intents", {})

            norm_file = pack_dir / "normalization.json"
            norm_data: dict[str, Any] = {}
            if norm_file.is_file():
                with open(norm_file, "r", encoding="utf-8") as f:
                    norm_data = json.load(f)

            return LanguagePack(
                code=lang_meta.get("code", pack_dir.name),
                name=lang_meta.get("name", pack_dir.name),
                english_name=lang_meta.get("english_name", pack_dir.name),
                direction=lang_meta.get("direction", "ltr"),
                version=lang_meta.get("version", "0.1.0"),
                responses=lang_meta.get("responses", {}),
                intents=intents_data,
                normalization=norm_data,
            )
        except Exception as e:
            logger.error("Failed to load language pack from %s: %s", pack_dir, e)
            return None

    def get_pack(self, lang_code: str) -> LanguagePack:
        """Get pack by language code or fallback to English/Persian."""
        if lang_code in self._packs:
            return self._packs[lang_code]
        if LANG_ENGLISH in self._packs:
            return self._packs[LANG_ENGLISH]
        if LANG_PERSIAN in self._packs:
            return self._packs[LANG_PERSIAN]
        # Return fallback empty pack
        return LanguagePack(
            code=lang_code,
            name=lang_code,
            english_name=lang_code,
            direction="ltr",
            version="0.1.0",
        )

    def get_available_languages(self) -> list[tuple[str, str, str]]:
        """Return list of (code, name, direction)."""
        return [(p.code, p.name, p.direction) for p in self._packs.values()]


_GLOBAL_LOADER: Optional[LanguageLoader] = None


def get_language_loader() -> LanguageLoader:
    """Retrieve global LanguageLoader instance."""
    global _GLOBAL_LOADER
    if _GLOBAL_LOADER is None:
        _GLOBAL_LOADER = LanguageLoader()
    return _GLOBAL_LOADER
