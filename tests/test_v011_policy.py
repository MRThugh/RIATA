"""
Tests for R.I.A.T.A v0.1.1 Policy & Safety Engine.
Author: Ali Kamrani (MRThugh)

Verifies:
- ALLOW for low-risk standard desktop actions
- CONFIRM for high-risk system operations
- DENY for malicious/destructive commands
- Custom policy rule extension
"""

import pytest
from app.core.constants import INTENT_OPEN_APPLICATION, INTENT_OPEN_FOLDER
from app.engine.intent import Intent
from app.policy.decision import (
    DECISION_ALLOW,
    DECISION_CONFIRM,
    DECISION_DENY,
    PolicyEvaluation,
)
from app.policy.engine import PolicyEngine, get_policy_engine


@pytest.fixture
def policy_engine():
    return get_policy_engine()


def test_policy_low_risk_actions(policy_engine):
    # Standard application opening is ALLOWED
    intent_app = Intent(name=INTENT_OPEN_APPLICATION, confidence=1.0, entities={"application": "firefox"})
    eval_app = policy_engine.evaluate(intent_app)
    assert eval_app.decision == DECISION_ALLOW
    assert eval_app.risk_level == "low"
    assert eval_app.is_allowed is True

    # Folder opening is ALLOWED
    intent_folder = Intent(name=INTENT_OPEN_FOLDER, confidence=1.0, entities={"folder": "Downloads"})
    eval_folder = policy_engine.evaluate(intent_folder)
    assert eval_folder.decision == DECISION_ALLOW


def test_policy_high_risk_actions(policy_engine):
    # High-risk system operation requires CONFIRM
    intent_shutdown = Intent(name="SHUTDOWN", confidence=1.0)
    eval_shutdown = policy_engine.evaluate(intent_shutdown)
    assert eval_shutdown.decision == DECISION_CONFIRM
    assert eval_shutdown.risk_level == "high"
    assert eval_shutdown.requires_confirmation is True

    # High-risk file deletion requires CONFIRM
    intent_del = Intent(name="DELETE_FILE", confidence=1.0)
    eval_del = policy_engine.evaluate(intent_del)
    assert eval_del.decision == DECISION_CONFIRM


def test_policy_denied_actions(policy_engine):
    # Dangerous commands marked is_dangerous are DENIED
    intent_danger = Intent(name="UNKNOWN", confidence=0.0, is_dangerous=True, raw_text="sudo rm -rf /")
    eval_danger = policy_engine.evaluate(intent_danger)
    assert eval_danger.decision == DECISION_DENY
    assert eval_danger.risk_level == "critical"
    assert eval_danger.is_denied is True


def test_policy_custom_rule():
    pe = PolicyEngine()

    # Rule: block specific action during quiet hours
    def custom_rule(intent: Intent):
        if intent.name == "RESTRICTED_APP":
            return PolicyEvaluation(decision=DECISION_DENY, risk_level="high", reason="App restricted")
        return None

    pe.add_rule(custom_rule)

    eval_res = pe.evaluate(Intent(name="RESTRICTED_APP", confidence=1.0))
    assert eval_res.decision == DECISION_DENY
    assert eval_res.reason == "App restricted"


def test_policy_confirmation_cycle_in_router():
    """Verify that a high-risk action prompts for confirmation and transitions to ALLOW upon 'yes'."""
    from app.engine.router import get_intent_router
    router = get_intent_router()
    router.reset_context()

    # Step 1: Simulate high-risk intent trigger
    shutdown_intent = Intent(name="SHUTDOWN", confidence=1.0, language="en")
    router.interaction_context.set_pending_confirmation(
        intent=shutdown_intent, action_label="shutdown system", language="en"
    )
    assert router.interaction_context.awaiting_confirmation is True

    # Step 2: User responds with "yes"
    output = router.process("yes")
    # Intent should be processed as the confirmed intent, not stuck in a confirmation loop
    assert output.intent.name == "SHUTDOWN"
    assert router.interaction_context.awaiting_confirmation is False

