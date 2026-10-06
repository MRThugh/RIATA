"""
Intent representation for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.constants import (
    CONFIDENCE_MEDIUM,
    INTENT_UNKNOWN,
)


@dataclass
class Intent:
    """
    Language-independent intent representation.

    Language understanding and action execution are separated.
    Both Persian and English eventually resolve to this same structure.
    """

    name: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    normalized_text: str = ""
    language: str = "en"
    is_clarification_needed: bool = False
    clarification_prompt: str = ""
    is_dangerous: bool = False

    @property
    def is_actionable(self) -> bool:
        """Determines if the intent has sufficient confidence and is safe."""
        return (
            self.name != INTENT_UNKNOWN
            and not self.is_dangerous
            and not self.is_clarification_needed
            and self.confidence >= CONFIDENCE_MEDIUM
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert intent to serializable dictionary."""
        return {
            "name": self.name,
            "confidence": round(self.confidence, 3),
            "entities": self.entities,
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "language": self.language,
            "is_clarification_needed": self.is_clarification_needed,
            "clarification_prompt": self.clarification_prompt,
            "is_dangerous": self.is_dangerous,
        }

    @classmethod
    def unknown(cls, raw_text: str, language: str = "en") -> "Intent":
        """Factory for unknown intent."""
        return cls(
            name=INTENT_UNKNOWN,
            confidence=0.0,
            entities={},
            raw_text=raw_text,
            normalized_text="",
            language=language,
        )
