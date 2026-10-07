"""
English custom language rules for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from typing import Any, Optional
from app.languages.rules import BaseLanguageRules


class EnglishRules(BaseLanguageRules):
    """Optional custom execution hooks for English."""

    def normalize(self, text: str) -> Optional[str]:
        return None

    def extract_entities(
        self, intent_name: str, text: str, raw_text: str = ""
    ) -> Optional[dict[str, Any]]:
        return None


rules = EnglishRules()
