"""
Policy Engine for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Risk-aware permission decisions: ALLOW, CONFIRM, DENY.
Prevents unauthorized or dangerous desktop operations.
"""

from typing import Callable, Optional

from app.core.logger import get_logger
from app.engine.intent import Intent
from app.policy.decision import (
    DECISION_ALLOW,
    DECISION_CONFIRM,
    DECISION_DENY,
    PolicyEvaluation,
)

logger = get_logger("riata.policy")

# Intents deemed higher risk requiring explicit confirmation before execution
HIGH_RISK_INTENTS: set[str] = {
    "SHUTDOWN",
    "RESTART",
    "POWEROFF",
    "DELETE_FILE",
    "DELETE_DIRECTORY",
}


class PolicyEngine:
    """Evaluates security risk and determines execution policy for intents."""

    def __init__(self) -> None:
        self._custom_rules: list[Callable[[Intent], Optional[PolicyEvaluation]]] = []

    def add_rule(self, rule: Callable[[Intent], Optional[PolicyEvaluation]]) -> None:
        """Add custom policy evaluation rule."""
        self._custom_rules.append(rule)

    def evaluate(self, intent: Intent) -> PolicyEvaluation:
        """Evaluate intent risk and return ALLOW, CONFIRM, or DENY decision."""
        # 1. Strictly block dangerous commands
        if intent.is_dangerous:
            logger.warning("Policy DENY: Dangerous command blocked: %s", intent.raw_text)
            return PolicyEvaluation(
                decision=DECISION_DENY,
                risk_level="critical",
                reason="Destructive or privileged system command blocked.",
            )

        # 2. Check custom rules
        for rule in self._custom_rules:
            res = rule(intent)
            if res is not None:
                return res

        # 3. Check high-risk actions requiring user confirmation
        if intent.name in HIGH_RISK_INTENTS:
            action_desc = intent.name.replace("_", " ").lower()
            logger.info("Policy CONFIRM: Intent %s requires user confirmation", intent.name)
            return PolicyEvaluation(
                decision=DECISION_CONFIRM,
                risk_level="high",
                action_label=action_desc,
                reason=f"Action '{intent.name}' has potential system impact and requires user confirmation.",
            )

        # 4. Standard desktop operations are allowed directly
        return PolicyEvaluation(
            decision=DECISION_ALLOW,
            risk_level="low",
            reason="Standard operation permitted.",
        )


_GLOBAL_POLICY_ENGINE: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Retrieve global PolicyEngine singleton."""
    global _GLOBAL_POLICY_ENGINE
    if _GLOBAL_POLICY_ENGINE is None:
        _GLOBAL_POLICY_ENGINE = PolicyEngine()
    return _GLOBAL_POLICY_ENGINE
