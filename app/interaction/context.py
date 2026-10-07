"""
Interaction Context management for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Maintains short-lived conversational state across turns
(numbered candidate disambiguation, confirmation prompts, clarification).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.core.constants import INTENT_OPEN_APPLICATION, INTENT_PLAY_MUSIC
from app.engine.intent import Intent
from app.languages.registry import LanguagePack, get_language_registry


class ContextState(str, Enum):
    IDLE = "IDLE"
    AWAITING_SELECTION = "AWAITING_SELECTION"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"


@dataclass
class InteractionContext:
    """Short-lived conversational state."""

    state: ContextState = ContextState.IDLE
    pending_intent: Optional[Intent] = None
    target_intent_name: str = ""
    candidates: list[str] = field(default_factory=list)
    entities: dict[str, Any] = field(default_factory=dict)
    action_label: str = ""
    language: str = "en"
    turn_count: int = 0

    @property
    def awaiting_selection(self) -> bool:
        return self.state == ContextState.AWAITING_SELECTION

    @property
    def awaiting_confirmation(self) -> bool:
        return self.state == ContextState.AWAITING_CONFIRMATION

    def set_pending_selection(
        self,
        intent_name: str,
        candidates: list[str],
        entities: Optional[dict[str, Any]] = None,
        language: str = "en",
    ) -> None:
        """Establish pending selection menu (e.g. numbered songs or files)."""
        self.state = ContextState.AWAITING_SELECTION
        self.target_intent_name = intent_name
        self.candidates = list(candidates)
        self.entities = dict(entities or {})
        self.language = language
        self.turn_count = 1

    def set_pending_confirmation(
        self, intent: Intent, action_label: str = "", language: str = "en"
    ) -> None:
        """Establish pending confirmation prompt for higher-risk operations."""
        self.state = ContextState.AWAITING_CONFIRMATION
        self.pending_intent = intent
        self.target_intent_name = intent.name
        self.action_label = action_label or intent.name
        self.language = language
        self.turn_count = 1

    def clear(self) -> None:
        """Reset short-lived conversational state."""
        self.state = ContextState.IDLE
        self.pending_intent = None
        self.target_intent_name = ""
        self.candidates.clear()
        self.entities.clear()
        self.action_label = ""
        self.turn_count = 0

    def evaluate_turn(
        self, raw_text: str, pack: Optional[LanguagePack] = None
    ) -> tuple[Optional[str], Any]:
        """
        Evaluate user input relative to the active short-lived interaction state.
        Returns:
            ("SELECT", selected_candidate)
            ("CONFIRM", pending_intent)
            ("CANCEL", None)
            (None, None) if not handled by context
        """
        cleaned = raw_text.strip().lower()
        if not cleaned:
            return None, None

        reg = get_language_registry()
        active_pack = pack or reg.get(self.language)

        # 1. Handling pending confirmation
        if self.awaiting_confirmation:
            if active_pack.is_confirmation(cleaned):
                confirmed_intent = self.pending_intent
                self.clear()
                return "CONFIRM", confirmed_intent
            elif active_pack.is_cancellation(cleaned):
                self.clear()
                return "CANCEL", None

        # 2. Handling pending selection
        if self.awaiting_selection:
            # Check cancellation first
            if active_pack.is_cancellation(cleaned):
                self.clear()
                return "CANCEL", None

            # Numeric or ordinal selection
            num: Optional[int] = None
            if cleaned.isdigit():
                num = int(cleaned)
            else:
                ordinals = dict(active_pack.get_ordinals())
                for code in reg.get_supported_codes():
                    ordinals.update(reg.get(code).get_ordinals())
                if cleaned in ordinals:
                    num = ordinals[cleaned]

            if num is not None and 1 <= num <= len(self.candidates):
                selected = self.candidates[num - 1]
                target_name = self.target_intent_name
                entities = dict(self.entities)
                if target_name == INTENT_PLAY_MUSIC:
                    entities["song"] = selected
                    entities["selected_path"] = selected
                elif target_name == INTENT_OPEN_APPLICATION:
                    entities["application"] = selected
                self.clear()
                return "SELECT", (target_name, selected, entities)

            # Match against candidate name substring
            for cand in self.candidates:
                if cleaned in str(cand).lower():
                    target_name = self.target_intent_name
                    entities = dict(self.entities)
                    if target_name == INTENT_PLAY_MUSIC:
                        entities["song"] = cand
                        entities["selected_path"] = cand
                    elif target_name == INTENT_OPEN_APPLICATION:
                        entities["application"] = cand
                    self.clear()
                    return "SELECT", (target_name, cand, entities)

        return None, None
