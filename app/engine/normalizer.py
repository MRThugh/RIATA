"""
Natural-language normalizer for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import re
from typing import Optional

from app.core.constants import LANG_ENGLISH, LANG_PERSIAN
from app.languages.loader import LanguagePack, get_language_loader


class Normalizer:
    """Normalizes raw user input across supported languages."""

    # Precompiled regexes
    _MULTI_SPACE_REGEX = re.compile(r"\s+")
    _PERSIAN_PUNCTUATION_REGEX = re.compile(r"[؟،؛!?.،]+")
    _ENGLISH_PUNCTUATION_REGEX = re.compile(r"[!?.,;:]+")

    def __init__(self) -> None:
        self.loader = get_language_loader()

    def normalize(self, text: str, language: str = LANG_ENGLISH) -> str:
        """Run full normalization pipeline for specified language."""
        if not text:
            return ""

        cleaned = text.strip()

        if language == LANG_PERSIAN:
            return self.normalize_persian(cleaned)
        elif language == LANG_ENGLISH:
            return self.normalize_english(cleaned)
        else:
            # Fallback standard normalization
            return self._clean_whitespace(cleaned.lower())

    def normalize_persian(self, text: str) -> str:
        """
        Normalize Persian text:
        - Arabic to Persian character conversion (ي -> ی, ك -> ک, ۀ -> ه, etc.)
        - Arabic and Persian digits to standard digits
        - Clean Arabic diacritics (harakat)
        - Normalize zero-width non-joiners to space or standardize
        - Normalize whitespace and repeated spaces
        - Strip common punctuation
        """
        pack: LanguagePack = self.loader.get_pack(LANG_PERSIAN)
        norm_cfg = pack.normalization

        result = text

        # 1. Character replacements
        char_replacements = norm_cfg.get("char_replacements", {})
        for orig, target in char_replacements.items():
            result = result.replace(orig, target)

        # 2. Digit replacements
        digit_replacements = norm_cfg.get("digit_replacements", {})
        for orig, target in digit_replacements.items():
            result = result.replace(orig, target)

        # 3. ZWNJ normalization (\u200c) -> single space
        result = result.replace("\u200c", " ")

        # 4. Strip punctuation
        result = self._PERSIAN_PUNCTUATION_REGEX.sub(" ", result)

        # 5. Clean whitespace
        result = self._clean_whitespace(result)

        return result

    def normalize_english(self, text: str) -> str:
        """
        Normalize English text:
        - Lowercase
        - Expand contractions
        - Strip punctuation
        - Clean whitespace
        """
        pack: LanguagePack = self.loader.get_pack(LANG_ENGLISH)
        norm_cfg = pack.normalization

        result = text.lower()

        # Expand contractions
        contractions = norm_cfg.get("contractions", {})
        for contr, expanded in contractions.items():
            result = result.replace(contr, expanded)

        # Strip punctuation
        result = self._ENGLISH_PUNCTUATION_REGEX.sub(" ", result)

        # Clean whitespace
        result = self._clean_whitespace(result)

        return result

    def strip_conversational_particles(self, text: str, language: str) -> str:
        """
        Strip polite prefixes/particles from the beginning of a command.
        Example: "لطفا فایرفاکس رو باز کن" -> "فایرفاکس رو باز کن"
        Example: "can you please open firefox" -> "open firefox"
        """
        pack = self.loader.get_pack(language)
        particles = pack.normalization.get("particles_to_strip", [])

        # Sort by length descending so longer phrases match first
        sorted_particles = sorted(particles, key=len, reverse=True)

        cleaned = text
        for p in sorted_particles:
            p_norm = self.normalize(p, language)
            if not p_norm:
                continue

            # Check if starts with particle
            pattern = rf"^{re.escape(p_norm)}\s+"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

            # Check if ends with polite particle
            end_pattern = rf"\s+{re.escape(p_norm)}$"
            cleaned = re.sub(end_pattern, "", cleaned, flags=re.IGNORECASE)

        return self._clean_whitespace(cleaned)

    @classmethod
    def _clean_whitespace(cls, text: str) -> str:
        """Replace multiple spaces/tabs/newlines with a single space and strip edges."""
        return cls._MULTI_SPACE_REGEX.sub(" ", text).strip()


_GLOBAL_NORMALIZER: Optional[Normalizer] = None


def get_normalizer() -> Normalizer:
    """Retrieve global Normalizer instance."""
    global _GLOBAL_NORMALIZER
    if _GLOBAL_NORMALIZER is None:
        _GLOBAL_NORMALIZER = Normalizer()
    return _GLOBAL_NORMALIZER
