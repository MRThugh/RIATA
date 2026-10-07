"""
Language rules interface for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Allows language packs to provide optional executable rules behind a clean,
isolated common interface without polluting the core engine.
"""

from abc import ABC
from typing import Any, Optional


class BaseLanguageRules(ABC):
    """Abstract base class for custom executable language-specific rules."""

    def normalize(self, text: str) -> Optional[str]:
        """
        Optional custom normalization hook.
        Return None to let the core declarative normalizer process the text.
        """
        return None

    def extract_entities(
        self, intent_name: str, text: str, raw_text: str = ""
    ) -> Optional[dict[str, Any]]:
        """
        Optional custom entity extraction hook.
        Return None to let the core declarative extractor process the text.
        """
        return None
