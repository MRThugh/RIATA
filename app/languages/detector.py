"""
Language detection module for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import re
from typing import Optional

from app.core.constants import LANG_AUTO, LANG_ENGLISH, LANG_PERSIAN

# Unicode ranges for Persian and Arabic scripts
PERSIAN_CHARS_REGEX = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_CHARS_REGEX = re.compile(r"[a-zA-Z]")


class LanguageDetector:
    """Lightweight local language detector."""

    def __init__(self, default_language: str = LANG_ENGLISH) -> None:
        self.default_language = default_language

    def detect(self, text: str) -> str:
        """
        Detect language of user input.

        Rules:
        - If input contains Persian characters (even if combined with English app names
          like 'Firefox رو باز کن'), it is treated as Persian.
        - If input contains only Latin characters or Latin dominant without Persian script,
          it is treated as English.
        - Fallbacks to default configured language.
        """
        if not text or not text.strip():
            return self.default_language

        persian_matches = len(PERSIAN_CHARS_REGEX.findall(text))
        latin_matches = len(LATIN_CHARS_REGEX.findall(text))

        # Persian script present -> Persian command
        if persian_matches > 0:
            return LANG_PERSIAN

        if latin_matches > 0:
            return LANG_ENGLISH

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
    if preferred and preferred != LANG_AUTO and preferred in (LANG_PERSIAN, LANG_ENGLISH):
        return preferred
    return get_language_detector().detect(text)
