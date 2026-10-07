"""
Language pack loader backward compatibility facade for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Delegates to LanguageRegistry while maintaining exact compatibility for
existing imports: LanguagePack, LanguageLoader, and get_language_loader.
"""

from pathlib import Path
from typing import Any, Optional

from app.languages.registry import (
    LanguagePack,
    LanguageRegistry,
    get_language_registry,
)


class LanguageLoader:
    """Compatibility facade wrapping LanguageRegistry."""

    def __init__(self, languages_dir: Optional[Path] = None) -> None:
        self.registry = get_language_registry()
        if languages_dir is not None:
            self.registry.discover(languages_dir)

    @property
    def languages_dir(self) -> Path:
        return self.registry.languages_dir

    @property
    def _packs(self) -> dict[str, LanguagePack]:
        return self.registry._packs

    def load_all(self) -> None:
        self.registry.discover()

    def get_pack(self, lang_code: str) -> LanguagePack:
        return self.registry.get(lang_code)

    def get_available_languages(self) -> list[tuple[str, str, str]]:
        return self.registry.get_available_languages()


_GLOBAL_LOADER: Optional[LanguageLoader] = None


def get_language_loader() -> LanguageLoader:
    """Retrieve global LanguageLoader instance."""
    global _GLOBAL_LOADER
    if _GLOBAL_LOADER is None:
        _GLOBAL_LOADER = LanguageLoader()
    return _GLOBAL_LOADER
