"""
Natural Response Engine for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Architecture:
Decouples intent execution and internal status reporting from user-facing natural language.
Understands:
- success & failure
- clarification & confirmation
- cancellation
- already-running states
- unavailable resources & invalid requests
- security/policy blocks
"""

from typing import Any, Optional

from app.core.constants import (
    INTENT_CLARIFY,
    INTENT_UNKNOWN,
    LANG_ENGLISH,
)
from app.engine.intent import Intent
from app.executor.result import (
    STATUS_APP_NOT_FOUND,
    STATUS_PATH_NOT_ALLOWED,
    STATUS_PERMISSION_DENIED,
    ExecutionResult,
)
from app.languages.registry import LanguagePack, get_language_registry
from app.policy.decision import PolicyEvaluation


class ResponseEngine:
    """Generates natural, deterministic user responses based on results and language packs."""

    def __init__(self) -> None:
        self.registry = get_language_registry()

    def generate(
        self,
        result: ExecutionResult,
        intent: Intent,
        policy: Optional[PolicyEvaluation] = None,
    ) -> str:
        """Format natural language response for the user."""
        lang = intent.language or LANG_ENGLISH
        pack: LanguagePack = self.registry.get(lang)

        # 1. Dangerous action blocked by security policy
        if intent.is_dangerous or (policy and policy.is_denied) or result.status == STATUS_PERMISSION_DENIED:
            return pack.get_response(
                "dangerous_command",
                default="⚠️ Action blocked for security reasons. R.I.A.T.A does not execute destructive actions.",
            )

        # 2. Confirmation required
        if policy and policy.requires_confirmation:
            action_label = policy.action_label or intent.name
            return pack.get_response(
                "confirm_action",
                default="Are you sure you want to {action}? (yes / no)",
                action=action_label,
            )

        # 3. Clarification requested
        if intent.is_clarification_needed or intent.name == INTENT_CLARIFY:
            if intent.clarification_prompt:
                return intent.clarification_prompt
            return pack.get_response(
                "clarify_general",
                default="Could you please clarify what you would like to do?",
            )

        # 4. Unknown intent
        if intent.name == INTENT_UNKNOWN:
            return pack.get_response(
                "unknown_intent",
                default="I didn't quite understand what you would like to do.",
            )

        # 5. Message key translation directly from Language Pack
        msg = pack.get_response(result.message_key, default="", **result.params)
        if not msg:
            # Fallback based on execution status
            if result.status == STATUS_APP_NOT_FOUND:
                app = result.params.get("app_name", "Application")
                msg = pack.get_response("app_not_found", default=f"Couldn't find {app}.", app_name=app)
            elif result.status == STATUS_PATH_NOT_ALLOWED:
                msg = pack.get_response("file_not_found", default="Target path is outside allowed sandbox.")
            elif result.success:
                msg = f"✓ {result.action_summary or 'Action completed.'}"
            else:
                msg = f"✕ {result.error or result.message or 'Action failed.'}"

        # 6. Append dry run indicator if applicable
        if result.is_dry_run:
            dry_suffix = pack.get_response(
                "dry_run_suffix",
                default=" [DRY RUN — NOT EXECUTED]",
            )
            msg += dry_suffix

        return msg


_GLOBAL_RESPONSE_ENGINE: Optional[ResponseEngine] = None


def get_response_engine() -> ResponseEngine:
    """Retrieve global ResponseEngine singleton."""
    global _GLOBAL_RESPONSE_ENGINE
    if _GLOBAL_RESPONSE_ENGINE is None:
        _GLOBAL_RESPONSE_ENGINE = ResponseEngine()
    return _GLOBAL_RESPONSE_ENGINE
