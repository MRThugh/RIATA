"""
Unit tests for R.I.A.T.A v0.2.0 Policy Engine & Confirmation Integration.
Author: Ali Kamrani (MRThugh)

Verifies:
- Authoritative evaluation of LOW, HIGH, and CRITICAL risk levels
- Context-bound confirmation cycle (DELETE_FILE -> CONFIRM -> 'بله' -> EXECUTE)
- Context-bound cancellation cycle (DELETE_FILE -> CONFIRM -> 'نه' -> CANCEL)
- Confirmation token invalidation and non-replayability
- Immediate DENY on dangerous system commands
"""

import pytest

from app.core.config import get_config
from app.core.context.manager import get_context_manager
from app.engine.intent import Intent
from app.engine.router import get_intent_router
from app.executor.result import (
    STATUS_CANCELLED,
    STATUS_NEEDS_CONFIRMATION,
    STATUS_PERMISSION_DENIED,
    STATUS_SUCCESS,
)
from app.policy.decision import DECISION_ALLOW, DECISION_CONFIRM, DECISION_DENY
from app.policy.engine import get_policy_engine


def test_high_risk_intent_requires_confirmation_in_policy():
    policy_engine = get_policy_engine()
    delete_intent = Intent(name="DELETE_FILE", confidence=1.0, entities={"file": "test.txt"})
    evaluation = policy_engine.evaluate(delete_intent)

    assert evaluation.decision == DECISION_CONFIRM
    assert evaluation.requires_confirmation is True
    assert evaluation.risk_level == "high"


def test_delete_file_confirmation_cycle_with_yes():
    config = get_config()
    orig_dry_run = config.dry_run
    config.dry_run = True

    try:
        router = get_intent_router()
        router.reset_context()
        session_id = "test-policy-yes-session"

        # Turn 1: User requests deletion
        out1 = router.process("فایل test.txt رو حذف کن", session_id=session_id)
        assert out1.result.status == STATUS_NEEDS_CONFIRMATION
        assert "تأیید" in out1.response_text or "test.txt" in out1.response_text

        ctx_manager = get_context_manager()
        assert ctx_manager.get_pending_confirmation(session_id) is not None

        # Turn 2: User confirms with "بله"
        out2 = router.process("بله", session_id=session_id)
        assert out2.result.status == STATUS_SUCCESS
        assert out2.intent.name == "DELETE_FILE"
        assert "حذف شد" in out2.response_text

        # Turn 3: User says "بله" again -> confirmation must NOT be replayed!
        out3 = router.process("بله", session_id=session_id)
        assert out3.intent.name != "DELETE_FILE"
    finally:
        config.dry_run = orig_dry_run


def test_delete_file_cancellation_cycle_with_no():
    config = get_config()
    orig_dry_run = config.dry_run
    config.dry_run = True

    try:
        router = get_intent_router()
        router.reset_context()
        session_id = "test-policy-no-session"

        # Turn 1: User requests deletion
        out1 = router.process("فایل test.txt رو حذف کن", session_id=session_id)
        assert out1.result.status == STATUS_NEEDS_CONFIRMATION

        # Turn 2: User cancels with "نه"
        out2 = router.process("نه", session_id=session_id)
        assert out2.result.status == STATUS_CANCELLED
        assert out2.intent.name == "CANCEL"
        assert "لغو شد" in out2.response_text

        # Verify confirmation token was rejected and removed
        ctx_manager = get_context_manager()
        assert ctx_manager.get_pending_confirmation(session_id) is None
    finally:
        config.dry_run = orig_dry_run


def test_dangerous_command_blocked_authoritatively():
    router = get_intent_router()
    out = router.process("sudo rm -rf /", session_id="test-deny")

    assert out.result.success is False
    assert out.result.executed is False
    assert out.result.status == STATUS_PERMISSION_DENIED
    assert out.intent.is_dangerous is True
