"""
Language detection module for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Language-agnostic detection leveraging registered Language Packs.
"""

import re
from typing import Optional

from app.core.constants import LANG_AUTO, LANG_ENGLISH
from app.languages.registry import get_language_registry

LATIN_CHARS_REGEX = re.compile(r"[a-zA-Z]")


class LanguageDetector:
    """Language-agnostic detector consulting registered Language Packs."""

    def __init__(self, default_language: str = LANG_ENGLISH) -> None:
        self.default_language = default_language
        self.registry = get_language_registry()

    def detect(self, text: str) -> str:
        """
        Detect language of user input.

        Rules:
        - Checks registered language packs with explicit script patterns.
          For example, if text contains Persian/Arabic characters, matches 'fa'.
        - If input contains Latin script, matches 'en' (or Latin pack).
        - Falls back to configured default language.
        """
        if not text or not text.strip():
            return self.default_language

        # 1. Check registered packs with custom script patterns
        for code in self.registry.get_supported_codes():
            pack = self.registry.get(code)
            if pack.script_pattern:
                matches = re.findall(pack.script_pattern, text)
                if matches:
                    return code

        # 2. Check Latin script for English or Latin-based registered pack
        if LATIN_CHARS_REGEX.search(text):
            if self.registry.has(LANG_ENGLISH):
                return LANG_ENGLISH
            # Return first available LTR language
            for code, _, direction in self.registry.get_available_languages():
                if direction == "ltr":
                    return code

        return self.default_language


_GLOBAL_DETECTOR: Optional[LanguageDetector] = None


def get_language_detector(default_lang: str = LANG_ENGLISH) -> LanguageDetector:
    """Retrieve the global language detector instance."""
    global _GLOBAL_DETECTOR
    if _GLOBAL_DETECTOR is None:
        _GLOBAL_DETECTOR = LanguageDetector(default_lang)
    return _GLOBAL_DETECTOR


def detect_language(text: str, preferred: str = LANG_AUTO) -> str:
    """Convenience helper to detect language from input string."""
    registry = get_language_registry()
    if preferred and preferred != LANG_AUTO and registry.has(preferred):
        return preferred
    return get_language_detector().detect(text)
