"""
Natural-language normalizer for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Architecture:
Language-agnostic normalization pipeline powered by declarative Language Packs.
Core does not hardcode language-specific if/elif branching.
"""

import re
from typing import Optional

from app.core.constants import LANG_ENGLISH, LANG_PERSIAN
from app.languages.registry import LanguagePack, get_language_registry


class Normalizer:
    """Normalizes user input dynamically using declarative rules from Language Packs."""

    _MULTI_SPACE_REGEX = re.compile(r"\s+")
    _DEFAULT_PUNCTUATION_REGEX = re.compile(r"[؟،؛!?.،:;\"']+")

    def __init__(self) -> None:
        self.registry = get_language_registry()

    def normalize(self, text: str, language: str = LANG_ENGLISH) -> str:
        """Run declarative normalization pipeline for the specified language pack."""
        if not text:
            return ""

        cleaned = text.strip()
        pack: LanguagePack = self.registry.get(language)

        # 1. Check custom rules hook if pack provides one
        if pack.rules:
            custom_norm = pack.rules.normalize(cleaned)
            if custom_norm is not None:
                return self._clean_whitespace(custom_norm)

        # 2. Declarative pipeline driven entirely by pack configuration
        norm_cfg = pack.normalization
        result = cleaned

        # 2a. Expand contractions (e.g. English "what's" -> "what is")
        contractions = norm_cfg.get("contractions", {})
        if contractions:
            lowered = result.lower()
            for contr, expanded in contractions.items():
                lowered = lowered.replace(contr.lower(), expanded)
            result = lowered

        # 2b. Character replacements (e.g. Persian/Arabic variants ي -> ی, ك -> ک, ۀ -> ه)
        char_replacements = norm_cfg.get("char_replacements", {})
        for orig, target in char_replacements.items():
            result = result.replace(orig, target)

        # 2c. Digit replacements (e.g. Persian/Arabic digits ۱۲۳ -> 123)
        digit_replacements = norm_cfg.get("digit_replacements", {})
        for orig, target in digit_replacements.items():
            result = result.replace(orig, target)

        # 2d. ZWNJ / zero-width non-joiner normalization
        if norm_cfg.get("normalize_zwnj", True):
            result = result.replace("\u200c", " ")

        # 2e. Lowercasing (if requested in pack, or default for LTR/English packs)
        should_lowercase = norm_cfg.get("lowercase", pack.direction == "ltr")
        if should_lowercase:
            result = result.lower()

        # 2f. Punctuation stripping from pack or fallback
        punct_pattern = norm_cfg.get("punctuation_pattern")
        if punct_pattern:
            result = re.sub(punct_pattern, " ", result)
        else:
            result = self._DEFAULT_PUNCTUATION_REGEX.sub(" ", result)

        # 2g. Clean whitespace
        return self._clean_whitespace(result)

    def normalize_persian(self, text: str) -> str:
        """Backward compatibility helper delegating to the Persian pack."""
        return self.normalize(text, LANG_PERSIAN)

    def normalize_english(self, text: str) -> str:
        """Backward compatibility helper delegating to the English pack."""
        return self.normalize(text, LANG_ENGLISH)

    def strip_conversational_particles(self, text: str, language: str) -> str:
        """
        Strip polite prefixes/particles dynamically defined in the language pack.
        Example: 'لطفا فایرفاکس رو باز کن' -> 'فایرفاکس رو باز کن'
        Example: 'can you please open firefox' -> 'open firefox'
        """
        pack = self.registry.get(language)
        particles = pack.normalization.get("particles_to_strip", [])
        if not particles:
            particles = pack.conversational.get("polite_prefixes", [])

        # Sort by length descending so longer multi-word phrases match first
        sorted_particles = sorted(particles, key=len, reverse=True)

        cleaned = text
        for p in sorted_particles:
            p_norm = self.normalize(p, language)
            if not p_norm:
                continue

            # Check if text starts with particle
            pattern = rf"^{re.escape(p_norm)}\s+"
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

            # Check if text ends with particle
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
