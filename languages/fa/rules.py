"""
Persian custom language rules for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)
"""

from typing import Any, Optional
from app.languages.rules import BaseLanguageRules


class PersianRules(BaseLanguageRules):
    """Optional custom execution hooks for Persian."""

    def normalize(self, text: str) -> Optional[str]:
        # Return None to use declarative normalization
        return None

    def extract_entities(
        self, intent_name: str, text: str, raw_text: str = ""
    ) -> Optional[dict[str, Any]]:
        # Return None to use declarative entity extraction
        return None


rules = PersianRules()
