"""
Intent Router and Execution Coordinator for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Architecture:
User Input
    ↓
Language System (Packs / Registry)
    ↓
Intent Engine (Parser / Matcher)
    ↓
Interaction System (Context / Disambiguation / Confirmation)
    ↓
Policy Engine (Risk Evaluation: ALLOW, CONFIRM, DENY)
    ↓
Capability Registry (Applications, Filesystem, Media, System)
    ↓
Response Engine (Natural localized response)
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.capabilities.registry import CapabilityRegistry, get_capability_registry
from app.core.constants import (
    INTENT_CANCEL,
    INTENT_CLARIFY,
    INTENT_CONFIRM,
    INTENT_EXIT_APPLICATION,
    INTENT_UNKNOWN,
)
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.engine.matcher import BaseIntentParser, get_intent_parser
from app.executor.result import (
    STATUS_EXECUTION_ERROR,
    STATUS_INVALID_COMMAND,
    STATUS_PERMISSION_DENIED,
    STATUS_SUCCESS,
    ExecutionResult,
)
from app.interaction.context import InteractionContext
from app.interaction.responses import ResponseEngine, get_response_engine
from app.languages.registry import LanguagePack, LanguageRegistry, get_language_registry
from app.policy.decision import DECISION_ALLOW, PolicyEvaluation
from app.policy.engine import PolicyEngine, get_policy_engine

logger = get_logger("riata.router")


@dataclass
class ProcessOutput:
    """End-to-end output of processing user input."""

    response_text: str
    intent: Intent
    result: Optional[ExecutionResult] = None
    is_exit: bool = False
    direction: str = "ltr"  # 'rtl' or 'ltr'


class IntentRouter:
    """
    Coordinates Intent understanding, Interaction context, Policy evaluations,
    Desktop capabilities, and Natural response generation.
    """

    def __init__(
        self,
        parser: Optional[BaseIntentParser] = None,
        policy_engine: Optional[PolicyEngine] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        response_engine: Optional[ResponseEngine] = None,
    ) -> None:
        self.parser = parser or get_intent_parser()
        self.policy_engine = policy_engine or get_policy_engine()
        self.capabilities = capability_registry or get_capability_registry()
        self.response_generator = response_engine or get_response_engine()
        self.loader: LanguageRegistry = get_language_registry()

        self.interaction_context = InteractionContext()
        self.context: dict[str, Any] = {}

    def process(self, user_input: str) -> ProcessOutput:
        """Parse user command, evaluate policy, execute safely, and respond naturally."""
        # 1. Check if user input is responding to an active interaction context
        context_action, context_payload = self.interaction_context.evaluate_turn(user_input)

        intent: Optional[Intent] = None
        is_user_confirmed = False
        if context_action == "CONFIRM":
            # User confirmed the pending high-risk intent!
            intent = context_payload
            is_user_confirmed = True
            logger.info("Confirmed pending intent: %s", intent.name if intent else "")
        elif context_action == "CANCEL":
            # User cancelled the pending interaction
            pack = self.loader.get(self.interaction_context.language)
            cancel_intent = Intent(
                name=INTENT_CANCEL,
                confidence=1.0,
                raw_text=user_input,
                language=self.interaction_context.language,
            )
            res = ExecutionResult(
                success=True,
                executed=False,
                status=STATUS_SUCCESS,
                intent_name=INTENT_CANCEL,
                message_key="action_cancelled",
                message="Action was cancelled.",
            )
            resp_text = self.response_generator.generate(res, cancel_intent)
            self.context.clear()
            return ProcessOutput(
                response_text=resp_text,
                intent=cancel_intent,
                result=res,
                direction=pack.direction,
            )
        elif context_action == "SELECT":
            target_name, selected_item, entities = context_payload
            pack = self.loader.get(self.interaction_context.language)
            intent = Intent(
                name=target_name,
                confidence=1.0,
                entities=entities,
                raw_text=user_input,
                normalized_text=str(selected_item),
                language=self.interaction_context.language,
            )

        # 2. If not consumed by context, parse intent normally
        if intent is None:
            intent = self.parser.parse(user_input, context=self.context)

        # Clear awaiting selection if consumed
        if self.context.get("awaiting_selection") and intent.name != INTENT_UNKNOWN:
            self.context.clear()

        # Get direction from active language pack
        pack: LanguagePack = self.loader.get(intent.language)
        direction = pack.direction

        # 3. Policy evaluation
        policy: PolicyEvaluation = self.policy_engine.evaluate(intent)

        # 3a. Dangerous or Denied by policy
        if intent.is_dangerous or policy.is_denied:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_PERMISSION_DENIED,
                intent_name=intent.name,
                message_key="dangerous_command",
                error="Action blocked for security reasons.",
                message="Action blocked for security reasons.",
            )
            response_text = self.response_generator.generate(res, intent, policy)
            return ProcessOutput(
                response_text=response_text,
                intent=intent,
                result=res,
                direction=direction,
            )

        # If user explicitly confirmed this high-risk intent in this turn, allow execution
        if is_user_confirmed and policy.requires_confirmation:
            policy = PolicyEvaluation(
                decision=DECISION_ALLOW,
                risk_level=policy.risk_level,
                action_label=policy.action_label,
                reason="User explicitly confirmed operation.",
            )

        # 3b. Confirmation required by policy
        if policy.requires_confirmation:
            self.interaction_context.set_pending_confirmation(
                intent=intent, action_label=policy.action_label, language=intent.language
            )
            self.context["awaiting_confirmation"] = True
            res = ExecutionResult(
                success=True,
                executed=False,
                status=STATUS_SUCCESS,
                intent_name=intent.name,
                message_key="confirm_action",
                params={"action": policy.action_label or intent.name},
                message=f"Confirmation required for {intent.name}",
            )
            response_text = self.response_generator.generate(res, intent, policy)
            return ProcessOutput(
                response_text=response_text,
                intent=intent,
                result=res,
                direction=direction,
            )

        # 4. Clarification needed
        if intent.is_clarification_needed:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=intent.name,
                message_key="clarify_general",
                message=intent.clarification_prompt or "Clarification required.",
            )
            response_text = self.response_generator.generate(res, intent)
            return ProcessOutput(
                response_text=response_text,
                intent=intent,
                result=res,
                direction=direction,
            )

        # 5. Unknown intent
        if intent.name == INTENT_UNKNOWN:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=intent.name,
                message_key="unknown_intent",
                message="Unknown command.",
            )
            response_text = self.response_generator.generate(res, intent)
            return ProcessOutput(
                response_text=response_text,
                intent=intent,
                result=res,
                direction=direction,
            )

        # 6. Route to desktop capability
        result = self._dispatch_capability(intent)

        # 7. Update context if executor requested follow-up / disambiguation
        if result.requires_context:
            self.context = dict(result.context_data)
            self.interaction_context.set_pending_selection(
                intent_name=result.context_data.get("intent", intent.name),
                candidates=result.context_data.get("candidates", []),
                entities=result.context_data.get("entities", {}),
                language=intent.language,
            )
        else:
            self.context.clear()
            self.interaction_context.clear()

        # 8. Natural response generation
        response_text = self.response_generator.generate(result, intent, policy)
        is_exit = intent.name == INTENT_EXIT_APPLICATION

        return ProcessOutput(
            response_text=response_text,
            intent=intent,
            result=result,
            is_exit=is_exit,
            direction=direction,
        )

    def _dispatch_capability(self, intent: Intent) -> ExecutionResult:
        """Route intent to matched Capability provider."""
        capability = self.capabilities.find_for_intent(intent.name)
        if capability:
            try:
                return capability.execute(intent)
            except Exception as e:
                logger.exception("Capability '%s' failed executing %s: %s", capability.id, intent.name, e)
                return ExecutionResult(
                    success=False,
                    executed=False,
                    status=STATUS_EXECUTION_ERROR,
                    intent_name=intent.name,
                    message_key="app_launch_failed",
                    params={"app_name": intent.name, "error": str(e)},
                    error=str(e),
                )

        # Unknown intent handler
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=intent.name,
            message_key="unknown_intent",
            params={},
        )

    def reset_context(self) -> None:
        """Clear active conversation context."""
        self.context.clear()
        self.interaction_context.clear()


_GLOBAL_ROUTER: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """Retrieve global IntentRouter singleton."""
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = IntentRouter()
    return _GLOBAL_ROUTER
