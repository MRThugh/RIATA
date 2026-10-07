"""
Intent Router, Context Coordinator, and Multi-Step Execution for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)

Architecture Pipeline:
User Input
    ↓
Language System (Packs / Detector / Normalizer)
    ↓
Context Engine & Pending Confirmation Check
    ↓
Command Planner (Multi-step Decomposition)
    ↓
Contextual Entity Resolution & Ambiguity Check
    ↓
Policy Engine (Authoritative: ALLOW, CONFIRM, DENY)
    ↓
Capability Registry (Standardized Capabilities)
    ↓
Executor (Zero shell invocation, Sandbox Verification)
    ↓
Result & Context Update
    ↓
Response Engine (Natural Localized Response)
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.capabilities.registry import CapabilityRegistry, get_capability_registry
from app.core.constants import (
    INTENT_CANCEL,
    INTENT_CLARIFY,
    INTENT_CLARIFY_AMBIGUITY,
    INTENT_CONFIRM,
    INTENT_EXIT_APPLICATION,
    INTENT_RESET_CONTEXT,
    INTENT_UNKNOWN,
)
from app.core.context.manager import ContextManager, get_context_manager
from app.core.context.models import SessionContext
from app.core.context.resolver import ContextualEntityResolver
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.engine.matcher import BaseIntentParser, get_intent_parser
from app.engine.planner import CommandPlan, CommandPlanner, CommandStep, get_command_planner
from app.executor.result import (
    STATUS_CANCELLED,
    STATUS_EXECUTION_ERROR,
    STATUS_FAILED,
    STATUS_INVALID_COMMAND,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_NEEDS_CONFIRMATION,
    STATUS_PARTIAL_SUCCESS,
    STATUS_PERMISSION_DENIED,
    STATUS_SUCCESS,
    ExecutionResult,
)
from app.interaction.context import InteractionContext
from app.interaction.responses import ResponseEngine, get_response_engine
from app.languages.detector import detect_language
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
    plan: Optional[CommandPlan] = None
    session_id: str = "default"


class IntentRouter:
    """
    Coordinates Intent understanding, Context Engine, Command Planner,
    Authoritative Policy evaluations, Desktop capabilities, and Natural responses.
    """

    def __init__(
        self,
        parser: Optional[BaseIntentParser] = None,
        policy_engine: Optional[PolicyEngine] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        response_engine: Optional[ResponseEngine] = None,
        planner: Optional[CommandPlanner] = None,
        context_manager: Optional[ContextManager] = None,
    ) -> None:
        self.parser = parser or get_intent_parser()
        self.policy_engine = policy_engine or get_policy_engine()
        self.capabilities = capability_registry or get_capability_registry()
        self.response_generator = response_engine or get_response_engine()
        self.loader: LanguageRegistry = get_language_registry()

        # v0.2.0 Context Engine and Command Planner
        self.context_manager = context_manager or get_context_manager()
        self.planner = planner or get_command_planner()
        self.resolver = ContextualEntityResolver()

        # Backwards compatibility state facades
        self.interaction_context = InteractionContext()
        self.context: dict[str, Any] = {}

    def process(self, user_input: str, session_id: str = "default") -> ProcessOutput:
        """
        Process user command through the full v0.2.0 deterministic pipeline.
        """
        out = self._do_process(user_input, session_id=session_id)
        try:
            self.context_manager.save_session(session_id)
        except Exception:
            pass
        return out

    def _do_process(self, user_input: str, session_id: str = "default") -> ProcessOutput:
        cleaned_input = (user_input or "").strip()
        session_ctx = self.context_manager.get_or_create(session_id)

        # Detect language early
        lang = detect_language(cleaned_input) if cleaned_input else "en"
        pack: LanguagePack = self.loader.get(lang)
        direction = pack.direction

        # =====================================================================
        # 1. Check for Context Reset Intent ("فراموشش کن", "reset context", etc.)
        # =====================================================================
        if cleaned_input.lower() in (
            "فراموشش کن",
            "فراموش کن",
            "شروع دوباره",
            "بازنشانی",
            "ریست",
            "لغو زمینه",
            "forget it",
            "forget",
            "reset context",
            "start over",
            "clear context",
        ):
            session_ctx.clear()
            self.context_manager.reset(session_id)
            self.reset_context()
            reset_intent = Intent(
                name=INTENT_RESET_CONTEXT,
                confidence=1.0,
                raw_text=cleaned_input,
                language=lang,
            )
            res = ExecutionResult(
                success=True,
                executed=False,
                status=STATUS_SUCCESS,
                intent_name=INTENT_RESET_CONTEXT,
                message_key="context_reset",
                message="Conversation context was reset.",
            )
            resp_text = self.response_generator.generate(res, reset_intent)
            return ProcessOutput(
                response_text=resp_text,
                intent=reset_intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        # =====================================================================
        # 2. Check for Active Pending Confirmation Token
        # =====================================================================
        pending_conf = self.context_manager.get_pending_confirmation(session_id)
        if pending_conf or self.interaction_context.awaiting_confirmation:
            lowered = cleaned_input.lower()
            if pack.is_confirmation(lowered) or lowered in ("yes", "y", "بله", "آره", "اره", "تایید"):
                confirmed_intent = None
                action_label = ""
                resumed_plan = getattr(session_ctx, "pending_plan", None)
                plan_step_idx = getattr(session_ctx, "pending_step_index", 0)

                if pending_conf:
                    # Verify action and entity fingerprint
                    confirmed_intent = self.context_manager.consume_pending_confirmation(
                        session_id=session_id,
                        confirmation_id=pending_conf.confirmation_id,
                        expected_intent_name=pending_conf.action,
                        expected_entities=pending_conf.entities,
                    )
                    action_label = pending_conf.action_label
                    self.interaction_context.clear()
                    self.context.clear()
                elif self.interaction_context.awaiting_confirmation:
                    confirmed_intent = self.interaction_context.pending_intent
                    action_label = self.interaction_context.action_label
                    self.interaction_context.clear()
                    self.context.clear()

                if confirmed_intent:
                    logger.info("Session '%s': Confirmed operation %s", session_id, confirmed_intent.name)
                    # Authoritative Policy re-check (Section 17): Confirmation must NEVER bypass policy!
                    policy = self.policy_engine.evaluate(confirmed_intent)
                    if confirmed_intent.is_dangerous or policy.is_denied:
                        logger.warning("Denied confirmed operation by security policy: %s", confirmed_intent.name)
                        session_ctx.pending_plan = None
                        res = ExecutionResult(
                            success=False,
                            executed=False,
                            status=STATUS_PERMISSION_DENIED,
                            intent_name=confirmed_intent.name,
                            message="Action blocked for security reasons.",
                            error="Action blocked for security reasons.",
                        )
                        resp_text = self.response_generator.generate(res, confirmed_intent, policy)
                        return ProcessOutput(
                            response_text=resp_text,
                            intent=confirmed_intent,
                            result=res,
                            direction=direction,
                            session_id=session_id,
                        )

                    # Dispatch to capability (includes capability validation contract check)
                    res = self._dispatch_capability(confirmed_intent)
                    session_ctx.record_turn(confirmed_intent, res)

                    # Multi-step resume if part of a pending plan (Section 18)
                    if resumed_plan and 0 <= plan_step_idx < len(resumed_plan.steps):
                        return self._resume_multi_step_plan(
                            resumed_plan, plan_step_idx, confirmed_intent, res, session_ctx, session_id, lang
                        )

                    resp_text = self.response_generator.generate(res, confirmed_intent)
                    self._sync_backwards_compat(session_ctx)
                    return ProcessOutput(
                        response_text=resp_text,
                        intent=confirmed_intent,
                        result=res,
                        direction=direction,
                        session_id=session_id,
                    )
            elif pack.is_cancellation(lowered) or lowered in ("no", "n", "نه", "خیر", "لغو", "کنسل"):
                if pending_conf:
                    self.context_manager.reject_pending_confirmation(session_id)
                session_ctx.pending_plan = None
                session_ctx.pending_step_index = 0
                self.interaction_context.clear()
                self.context.clear()
                logger.info("Session '%s': Cancelled pending confirmation", session_id)
                cancel_intent = Intent(
                    name=INTENT_CANCEL,
                    confidence=1.0,
                    raw_text=cleaned_input,
                    language=lang,
                )
                res = ExecutionResult(
                    success=True,
                    executed=False,
                    status=STATUS_CANCELLED,
                    intent_name=INTENT_CANCEL,
                    message_key="action_cancelled",
                    message="Action was cancelled.",
                )
                resp_text = self.response_generator.generate(res, cancel_intent)
                self._sync_backwards_compat(session_ctx)
                return ProcessOutput(
                    response_text=resp_text,
                    intent=cancel_intent,
                    result=res,
                    direction=direction,
                    session_id=session_id,
                )

        # =====================================================================
        # 3. Check for Backwards-Compatible InteractionContext Turn Evaluation
        # =====================================================================
        context_action, context_payload = self.interaction_context.evaluate_turn(cleaned_input)
        if context_action == "CANCEL":
            cancel_intent = Intent(
                name=INTENT_CANCEL,
                confidence=1.0,
                raw_text=cleaned_input,
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
                direction=direction,
                session_id=session_id,
            )
        elif context_action == "SELECT":
            target_name, selected_item, entities = context_payload
            selected_intent = Intent(
                name=target_name,
                confidence=1.0,
                entities=entities,
                raw_text=cleaned_input,
                normalized_text=str(selected_item),
                language=self.interaction_context.language,
            )
            res = self._dispatch_capability(selected_intent)
            session_ctx.record_turn(selected_intent, res)
            resp_text = self.response_generator.generate(res, selected_intent)
            self.interaction_context.clear()
            self._sync_backwards_compat(session_ctx)
            return ProcessOutput(
                response_text=resp_text,
                intent=selected_intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        # =====================================================================
        # 4. Check for Open State Declaration ("Chrome و Firefox باز هستند")
        # =====================================================================
        declared_apps = self.resolver._detect_open_state_declaration(cleaned_input.lower(), lang)
        if declared_apps and not any(kw in cleaned_input.lower() for kw in ("ببند", "باز کن", "اجرا", "close", "open")):
            session_ctx.open_applications = declared_apps
            app_list_str = " و ".join(declared_apps) if lang == "fa" else ", ".join(declared_apps)
            ack_text = (
                f"متوجه شدم. برنامه‌های {app_list_str} در وضعیت باز ثبت شدند."
                if lang == "fa"
                else f"Understood. {app_list_str} recorded as currently open."
            )
            state_intent = Intent(
                name="SHOW_SYSTEM_INFO",
                confidence=1.0,
                raw_text=cleaned_input,
                language=lang,
            )
            res = ExecutionResult(
                success=True,
                executed=False,
                status=STATUS_SUCCESS,
                message=ack_text,
            )
            return ProcessOutput(
                response_text=ack_text,
                intent=state_intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        # =====================================================================
        # 5. Build Command Plan (Single or Multi-Step)
        # =====================================================================
        plan = self.planner.build_plan(cleaned_input, context=session_ctx)

        # Plan size rejection (Section 21: Never silently truncate user commands)
        if plan.status == "PLAN_TOO_LARGE":
            max_allowed = plan.metadata.get("max_allowed", 5)
            clause_cnt = plan.metadata.get("clause_count", 0)
            msg = (
                f"تعداد مراحل دستور ({clause_cnt}) بیش از سقف مجاز ({max_allowed}) است. لطفاً دستور را به بخش‌های ساده‌تر تقسیم کنید."
                if lang == "fa"
                else f"Command contains too many steps ({clause_cnt}). Maximum allowed is {max_allowed}. Please simplify your command."
            )
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=INTENT_UNKNOWN,
                message=msg,
                error=msg,
            )
            return ProcessOutput(
                response_text=msg,
                intent=plan.steps[0].intent if plan.steps else Intent.unknown(cleaned_input),
                result=res,
                direction=direction,
                plan=plan,
                session_id=session_id,
            )

        # Case 5A: Single-Step Plan
        if plan.is_single_step:
            step = plan.steps[0]
            output = self._process_single_step(step, session_ctx, session_id, lang)
            output.plan = plan
            return output

        # Case 5B: Multi-Step Plan ("Chrome رو باز کن و GitHub رو باز کن")
        return self._process_multi_step_plan(plan, session_ctx, session_id, lang)

    def _process_single_step(
        self,
        step: CommandStep,
        session_ctx: SessionContext,
        session_id: str,
        lang: str,
    ) -> ProcessOutput:
        """Execute single intent step through resolver, policy, and capability."""
        intent = step.intent
        pack = self.loader.get(intent.language or lang)
        direction = pack.direction

        # 1. Resolve Contextual Entities (pronouns, active app, active dir, ambiguity)
        res_result = self.resolver.resolve(
            raw_text=step.raw_text,
            parsed_intent_name=intent.name,
            extracted_entities=intent.entities,
            context=session_ctx,
            language=intent.language or lang,
        )

        # 1a. Ambiguity handling (e.g. "Chrome و Firefox باز هستند" -> "ببندش")
        if res_result.is_ambiguous:
            logger.info("Ambiguity detected for command: %s", step.raw_text)
            ambiguity_intent = Intent(
                name=INTENT_CLARIFY_AMBIGUITY,
                confidence=1.0,
                raw_text=step.raw_text,
                language=intent.language,
                is_clarification_needed=True,
                clarification_prompt=res_result.clarification_prompt,
            )
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_NEEDS_CLARIFICATION,
                intent_name=INTENT_CLARIFY_AMBIGUITY,
                message=res_result.clarification_prompt,
            )
            return ProcessOutput(
                response_text=res_result.clarification_prompt,
                intent=ambiguity_intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        if res_result.resolved and res_result.entities:
            intent.entities.update(res_result.entities)
            step.entities.update(res_result.entities)

        # 2. Policy Evaluation
        policy: PolicyEvaluation = self.policy_engine.evaluate(intent)

        # 2a. Dangerous or Denied by Security Policy
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
            resp_text = self.response_generator.generate(res, intent, policy)
            step.status = "BLOCKED"
            step.result = res
            return ProcessOutput(
                response_text=resp_text,
                intent=intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        # 2b. High-Risk Action Requiring User Confirmation
        if policy.requires_confirmation:
            conf_token = self.context_manager.set_pending_confirmation(
                session_id=session_id,
                intent=intent,
                action_label=policy.action_label,
            )
            self.context["awaiting_confirmation"] = True
            self.interaction_context.set_pending_confirmation(
                intent=intent, action_label=policy.action_label, language=intent.language
            )

            # Localized confirmation message formatting
            if intent.name == "DELETE_FILE" and intent.entities.get("file"):
                conf_msg = pack.get_response(
                    "confirm_delete_file",
                    default=f"Are you sure you want to delete {intent.entities['file']}? (yes / no)",
                    file_name=intent.entities["file"],
                )
            else:
                conf_msg = pack.get_response(
                    "confirm_action",
                    default="Are you sure you want to {action}? (yes / no)",
                    action=policy.action_label or intent.name,
                )

            res = ExecutionResult(
                success=True,
                executed=False,
                status=STATUS_NEEDS_CONFIRMATION,
                intent_name=intent.name,
                message_key="confirm_action",
                params={"action": policy.action_label or intent.name},
                message=conf_msg,
                metadata={"confirmation_id": conf_token.confirmation_id},
            )
            step.status = "PENDING"
            step.result = res
            return ProcessOutput(
                response_text=conf_msg,
                intent=intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        # 2c. Clarification Needed
        if intent.is_clarification_needed:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=intent.name,
                message_key="clarify_general",
                message=intent.clarification_prompt or "Clarification required.",
            )
            resp_text = self.response_generator.generate(res, intent)
            step.status = "FAILED"
            step.result = res
            return ProcessOutput(
                response_text=resp_text,
                intent=intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        # 2d. Unknown Intent
        if intent.name == INTENT_UNKNOWN:
            res = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_INVALID_COMMAND,
                intent_name=intent.name,
                message_key="unknown_intent",
                message="Unknown command.",
            )
            resp_text = self.response_generator.generate(res, intent)
            step.status = "FAILED"
            step.result = res
            return ProcessOutput(
                response_text=resp_text,
                intent=intent,
                result=res,
                direction=direction,
                session_id=session_id,
            )

        # 3. Route to Capability
        result = self._dispatch_capability(intent)
        step.result = result
        step.status = "SUCCESS" if result.success else "FAILED"

        # 4. Context Follow-up or Disambiguation
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

        # Update Session Context turn state
        session_ctx.record_turn(intent, result)
        self._sync_backwards_compat(session_ctx)

        # 5. Natural Localized Response
        resp_text = self.response_generator.generate(result, intent, policy)
        is_exit = intent.name == INTENT_EXIT_APPLICATION

        return ProcessOutput(
            response_text=resp_text,
            intent=intent,
            result=result,
            is_exit=is_exit,
            direction=direction,
            session_id=session_id,
        )

    def _process_multi_step_plan(
        self,
        plan: CommandPlan,
        session_ctx: SessionContext,
        session_id: str,
        lang: str,
    ) -> ProcessOutput:
        """
        Execute multi-step plan sequentially with strict step failure isolation.
        """
        pack = self.loader.get(lang)
        direction = pack.direction
        step_responses: list[str] = []
        any_failed = False
        any_success = False

        for i, step in enumerate(plan.steps):
            intent = step.intent

            # 1. Dependency enforcement (Section 20)
            if step.dependencies:
                dep_blocked = False
                blocking_step = None
                for dep in step.dependencies:
                    pred = (
                        plan.steps[dep]
                        if 0 <= dep < len(plan.steps)
                        else next((s for s in plan.steps if s.step_id == dep), None)
                    )
                    if not pred or pred.status != "SUCCESS":
                        dep_blocked = True
                        blocking_step = pred
                        break
                if dep_blocked:
                    pred_status = blocking_step.status if blocking_step else "UNKNOWN"
                    step.status = "BLOCKED" if pred_status in ("FAILED", "BLOCKED") else "SKIPPED"
                    step.error = f"Prerequisite step was not successful (status: {pred_status})."
                    step.result = ExecutionResult(
                        success=False,
                        executed=False,
                        status=STATUS_FAILED,
                        intent_name=intent.name,
                        message=step.error,
                        error=step.error,
                    )
                    step_responses.append(f"✕ {intent.name}: {step.error}")
                    any_failed = True
                    self._mark_remaining_steps(plan.steps[i + 1:], "SKIPPED")
                    break

            # 2. Resolve Contextual Entities per step
            res_result = self.resolver.resolve(
                raw_text=step.raw_text,
                parsed_intent_name=intent.name,
                extracted_entities=intent.entities,
                context=session_ctx,
                language=intent.language or lang,
            )
            if res_result.resolved and res_result.entities:
                intent.entities.update(res_result.entities)
                step.entities.update(res_result.entities)

            # 3. Policy Check
            policy: PolicyEvaluation = self.policy_engine.evaluate(intent)
            if intent.is_dangerous or policy.is_denied:
                step.status = "BLOCKED"
                step.result = ExecutionResult(
                    success=False,
                    executed=False,
                    status=STATUS_PERMISSION_DENIED,
                    intent_name=intent.name,
                    message="Blocked by security policy.",
                )
                step_responses.append(f"✕ {intent.name}: Action blocked for security reasons.")
                any_failed = True
                self._mark_remaining_steps(plan.steps[i + 1:], "SKIPPED")
                break

            if policy.requires_confirmation:
                # Multi-step command paused for confirmation (Section 18)
                self.context_manager.set_pending_confirmation(
                    session_id=session_id,
                    intent=intent,
                    action_label=policy.action_label,
                    plan_id=plan.plan_id,
                )
                session_ctx.pending_plan = plan
                session_ctx.pending_step_index = i
                step.status = "PENDING"
                conf_msg = pack.get_response(
                    "confirm_action",
                    default="Are you sure you want to {action}? (yes / no)",
                    action=policy.action_label or intent.name,
                )
                step_responses.append(f"⚠️ {conf_msg}")
                # Pauses execution cleanly: remaining steps wait for user confirmation
                break

            # 4. Execute Capability (with contract validation)
            step_res = self._dispatch_capability(intent)
            step.result = step_res

            if step_res.success:
                step.status = "SUCCESS"
                any_success = True
                session_ctx.record_turn(intent, step_res)
                msg = self.response_generator.generate(step_res, intent, policy)
                step_responses.append(msg)
            else:
                step.status = "FAILED"
                step.error = step_res.error or step_res.message
                any_failed = True
                msg = self.response_generator.generate(step_res, intent, policy)
                step_responses.append(msg)
                # Failure isolation: Do not execute subsequent dependent steps!
                self._mark_remaining_steps(plan.steps[i + 1:], "SKIPPED")
                break

        # Determine overall plan status
        if any_success and not any_failed:
            plan.status = "SUCCESS"
            overall_status = STATUS_SUCCESS
        elif any_success and any_failed:
            plan.status = "PARTIAL_SUCCESS"
            overall_status = STATUS_PARTIAL_SUCCESS
        else:
            plan.status = "FAILED"
            overall_status = STATUS_FAILED

        joined_response = "\n".join(step_responses)
        combined_result = ExecutionResult(
            success=any_success,
            executed=any_success,
            status=overall_status,
            intent_name="MULTI_STEP_PLAN",
            message=joined_response,
            data={"steps_count": len(plan.steps), "plan_status": plan.status},
        )

        return ProcessOutput(
            response_text=joined_response,
            intent=plan.steps[0].intent,
            result=combined_result,
            direction=direction,
            plan=plan,
            session_id=session_id,
        )

    def _resume_multi_step_plan(
        self,
        plan: CommandPlan,
        confirmed_step_idx: int,
        confirmed_intent: Intent,
        confirmed_result: ExecutionResult,
        session_ctx: SessionContext,
        session_id: str,
        lang: str,
    ) -> ProcessOutput:
        """
        Resume multi-step plan after explicit user confirmation of paused step.
        Executes remaining eligible steps through full pipeline (resolver, policy, capability validation).
        """
        pack = self.loader.get(lang)
        direction = pack.direction
        step_responses: list[str] = []

        confirmed_step = plan.steps[confirmed_step_idx]
        confirmed_step.result = confirmed_result

        if confirmed_result.success:
            confirmed_step.status = "SUCCESS"
            msg = self.response_generator.generate(confirmed_result, confirmed_intent)
            step_responses.append(msg)
        else:
            confirmed_step.status = "FAILED"
            confirmed_step.error = confirmed_result.error or confirmed_result.message
            msg = self.response_generator.generate(confirmed_result, confirmed_intent)
            step_responses.append(msg)
            self._mark_remaining_steps(plan.steps[confirmed_step_idx + 1:], "SKIPPED")
            session_ctx.pending_plan = None
            session_ctx.pending_step_index = 0
            return ProcessOutput(
                response_text="\n".join(step_responses),
                intent=confirmed_intent,
                result=confirmed_result,
                direction=direction,
                plan=plan,
                session_id=session_id,
            )

        any_failed = False
        any_success = True

        for i in range(confirmed_step_idx + 1, len(plan.steps)):
            step = plan.steps[i]
            intent = step.intent

            # Dependency enforcement
            if step.dependencies:
                dep_blocked = False
                blocking_step = None
                for dep in step.dependencies:
                    pred = (
                        plan.steps[dep]
                        if 0 <= dep < len(plan.steps)
                        else next((s for s in plan.steps if s.step_id == dep), None)
                    )
                    if not pred or pred.status != "SUCCESS":
                        dep_blocked = True
                        blocking_step = pred
                        break
                if dep_blocked:
                    pred_status = blocking_step.status if blocking_step else "UNKNOWN"
                    step.status = "BLOCKED" if pred_status in ("FAILED", "BLOCKED") else "SKIPPED"
                    step.error = f"Prerequisite step was not successful (status: {pred_status})."
                    step.result = ExecutionResult(
                        success=False,
                        executed=False,
                        status=STATUS_FAILED,
                        intent_name=intent.name,
                        message=step.error,
                        error=step.error,
                    )
                    step_responses.append(f"✕ {intent.name}: {step.error}")
                    any_failed = True
                    self._mark_remaining_steps(plan.steps[i + 1:], "SKIPPED")
                    break

            # Resolve Contextual Entities per step
            res_result = self.resolver.resolve(
                raw_text=step.raw_text,
                parsed_intent_name=intent.name,
                extracted_entities=intent.entities,
                context=session_ctx,
                language=intent.language or lang,
            )
            if res_result.resolved and res_result.entities:
                intent.entities.update(res_result.entities)
                step.entities.update(res_result.entities)

            # Policy Check
            policy = self.policy_engine.evaluate(intent)
            if intent.is_dangerous or policy.is_denied:
                step.status = "BLOCKED"
                step.result = ExecutionResult(
                    success=False,
                    executed=False,
                    status=STATUS_PERMISSION_DENIED,
                    intent_name=intent.name,
                    message="Blocked by security policy.",
                )
                step_responses.append(f"✕ {intent.name}: Action blocked for security reasons.")
                any_failed = True
                self._mark_remaining_steps(plan.steps[i + 1:], "SKIPPED")
                break

            if policy.requires_confirmation:
                self.context_manager.set_pending_confirmation(
                    session_id=session_id,
                    intent=intent,
                    action_label=policy.action_label,
                    plan_id=plan.plan_id,
                )
                session_ctx.pending_plan = plan
                session_ctx.pending_step_index = i
                step.status = "PENDING"
                conf_msg = pack.get_response(
                    "confirm_action",
                    default="Are you sure you want to {action}? (yes / no)",
                    action=policy.action_label or intent.name,
                )
                step_responses.append(f"⚠️ {conf_msg}")
                return ProcessOutput(
                    response_text="\n".join(step_responses),
                    intent=intent,
                    result=ExecutionResult(
                        success=True,
                        executed=False,
                        status=STATUS_NEEDS_CONFIRMATION,
                        intent_name=intent.name,
                        message=conf_msg,
                    ),
                    direction=direction,
                    plan=plan,
                    session_id=session_id,
                )

            # Execute Capability with contract validation
            step_res = self._dispatch_capability(intent)
            step.result = step_res

            if step_res.success:
                step.status = "SUCCESS"
                any_success = True
                session_ctx.record_turn(intent, step_res)
                msg = self.response_generator.generate(step_res, intent, policy)
                step_responses.append(msg)
            else:
                step.status = "FAILED"
                step.error = step_res.error or step_res.message
                any_failed = True
                msg = self.response_generator.generate(step_res, intent, policy)
                step_responses.append(msg)
                self._mark_remaining_steps(plan.steps[i + 1:], "SKIPPED")
                break

        # Invalidate pending plan once fully completed
        session_ctx.pending_plan = None
        session_ctx.pending_step_index = 0

        if any_success and not any_failed:
            plan.status = "SUCCESS"
            overall_status = STATUS_SUCCESS
        elif any_success and any_failed:
            plan.status = "PARTIAL_SUCCESS"
            overall_status = STATUS_PARTIAL_SUCCESS
        else:
            plan.status = "FAILED"
            overall_status = STATUS_FAILED

        joined_response = "\n".join(step_responses)
        combined_result = ExecutionResult(
            success=any_success,
            executed=any_success,
            status=overall_status,
            intent_name="MULTI_STEP_PLAN",
            message=joined_response,
            data={"steps_count": len(plan.steps), "plan_status": plan.status},
        )

        return ProcessOutput(
            response_text=joined_response,
            intent=plan.steps[0].intent,
            result=combined_result,
            direction=direction,
            plan=plan,
            session_id=session_id,
        )

    def _mark_remaining_steps(self, steps: list[CommandStep], status: str) -> None:
        """Mark subsequent unexecuted steps as SKIPPED or CANCELLED."""
        for step in steps:
            step.status = status
            step.result = ExecutionResult(
                success=False,
                executed=False,
                status=STATUS_FAILED,
                intent_name=step.intent.name,
                message=f"Step was not executed because a prior step {status.lower()}.",
            )

    def _dispatch_capability(self, intent: Intent) -> ExecutionResult:
        """Route intent to matched Capability provider with validation contract."""
        capability = self.capabilities.find_for_intent(intent.name)
        if capability:
            # Capability validate contract (Section 23)
            is_valid, err_msg = capability.validate(intent)
            if not is_valid:
                logger.warning(
                    "Capability '%s' validation rejected intent '%s': %s",
                    capability.id,
                    intent.name,
                    err_msg,
                )
                return ExecutionResult(
                    success=False,
                    executed=False,
                    status=STATUS_INVALID_COMMAND,
                    intent_name=intent.name,
                    error=err_msg or "Capability validation failed.",
                    message=err_msg or "Invalid parameters for command.",
                )

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

    def _sync_backwards_compat(self, session_ctx: SessionContext) -> None:
        """Keep v0.1.1 legacy context dictionaries in sync for backwards compatibility."""
        self.context["active_application"] = session_ctx.active_application
        self.context["active_directory"] = session_ctx.active_directory
        self.context["active_file"] = session_ctx.active_file

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
