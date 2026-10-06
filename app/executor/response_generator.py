"""
Localized response generation for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from typing import Optional

from app.core.constants import (
    INTENT_CLARIFY,
    INTENT_UNKNOWN,
    LANG_ENGLISH,
    LANG_PERSIAN,
)
from app.engine.intent import Intent
from app.executor.result import ExecutionResult
from app.languages.loader import LanguagePack, get_language_loader


class ResponseGenerator:
    """Translates language-agnostic ExecutionResults into localized natural language."""

    def __init__(self) -> None:
        self.loader = get_language_loader()

    def generate(self, result: ExecutionResult, intent: Intent) -> str:
        """Format a natural language response for the user."""
        lang = intent.language or LANG_ENGLISH
        pack: LanguagePack = self.loader.get_pack(lang)

        # 1. Dangerous action blocked
        if intent.is_dangerous:
            return pack.get_response("dangerous_command", default="⚠️ Action blocked for safety.")

        # 2. Clarification needed
        if intent.is_clarification_needed:
            if intent.clarification_prompt:
                return intent.clarification_prompt
            return pack.get_response("clarify_general", default="Could you please clarify?")

        # 3. Unknown intent
        if intent.name == INTENT_UNKNOWN:
            return pack.get_response(
                "unknown_intent",
                default="I didn't understand what you would like to do.",
            )

        # 4. Message key translation from pack
        msg = pack.get_response(result.message_key, default="", **result.params)
        if not msg:
            # Fallback if specific key is empty
            if result.success:
                msg = f"✓ {result.action_summary}"
            else:
                msg = f"✕ {result.error or 'Action failed'}"

        # 5. Append dry run indicator if applicable
        if result.is_dry_run:
            dry_suffix = pack.get_response(
                "dry_run_suffix",
                default=" [DRY RUN — NOT EXECUTED]",
            )
            msg += dry_suffix

        return msg


_GLOBAL_RESPONSE_GEN: Optional[ResponseGenerator] = None


def get_response_generator() -> ResponseGenerator:
    """Retrieve global ResponseGenerator instance."""
    global _GLOBAL_RESPONSE_GEN
    if _GLOBAL_RESPONSE_GEN is None:
        _GLOBAL_RESPONSE_GEN = ResponseGenerator()
    return _GLOBAL_RESPONSE_GEN
