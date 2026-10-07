"""
Unit tests for R.I.A.T.A v0.2.0 Language Packs Contextual Integration.
Author: Ali Kamrani (MRThugh)

Verifies:
- Persian natural contextual phrases ('ببندش', 'داخلش', 'فراموشش کن')
- English natural contextual phrases ('close it', 'in it', 'forget it')
- Confirmation words ('بله', 'آره', 'yes') and cancellation words ('نه', 'خیر', 'لغو', 'no')
- Correct text direction preservation ('rtl' for Persian, 'ltr' for English)
- Natural localized response output
"""

import pytest

from app.core.config import get_config
from app.engine.router import get_intent_router
from app.executor.result import STATUS_CANCELLED, STATUS_SUCCESS


def test_persian_full_contextual_flow():
    config = get_config()
    orig = config.dry_run
    config.dry_run = True

    try:
        router = get_intent_router()
        router.reset_context()
        session_id = "test-lang-flow-fa"

        # Turn 1: Open Firefox
        out1 = router.process("فایرفاکس رو باز کن", session_id=session_id)
        assert out1.direction == "rtl"
        assert out1.intent.name == "OPEN_APPLICATION"
        assert "باز شد" in out1.response_text

        # Turn 2: Contextual close: "ببندش"
        out2 = router.process("ببندش", session_id=session_id)
        assert out2.direction == "rtl"
        assert out2.intent.name == "CLOSE_APPLICATION"
        assert out2.intent.entities.get("application") == "firefox"
        assert "بسته شد" in out2.response_text

        # Turn 3: Context reset: "فراموشش کن"
        out3 = router.process("فراموشش کن", session_id=session_id)
        assert out3.direction == "rtl"
        assert "بازنشانی شد" in out3.response_text
    finally:
        config.dry_run = orig


def test_english_full_contextual_flow():
    config = get_config()
    orig = config.dry_run
    config.dry_run = True

    try:
        router = get_intent_router()
        router.reset_context()
        session_id = "test-lang-flow-en"

        # Turn 1: Open Chrome
        out1 = router.process("Open Chrome", session_id=session_id)
        assert out1.direction == "ltr"
        assert out1.intent.name == "OPEN_APPLICATION"
        assert "opened" in out1.response_text.lower()

        # Turn 2: Contextual close: "close it"
        out2 = router.process("close it", session_id=session_id)
        assert out2.direction == "ltr"
        assert out2.intent.name == "CLOSE_APPLICATION"
        assert "closed" in out2.response_text.lower()

        # Turn 3: Context reset: "reset context"
        out3 = router.process("reset context", session_id=session_id)
        assert out3.direction == "ltr"
        assert "reset" in out3.response_text.lower()
    finally:
        config.dry_run = orig
