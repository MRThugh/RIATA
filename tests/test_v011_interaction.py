"""
Tests for R.I.A.T.A v0.1.1 Interaction System.
Author: Ali Kamrani (MRThugh)

Verifies:
- Short-lived interaction context retention
- Disambiguation numbered selection (1, 2) and ordinals ('اول', 'first')
- Confirmation flow ('بله' / 'yes')
- Cancellation flow ('نه' / 'cancel')
- Natural Response Engine
"""

import pytest
from app.core.constants import INTENT_CANCEL, INTENT_OPEN_APPLICATION, INTENT_PLAY_MUSIC
from app.engine.intent import Intent
from app.engine.router import get_intent_router
from app.executor.result import STATUS_SUCCESS, ExecutionResult
from app.interaction.context import InteractionContext
from app.interaction.responses import get_response_engine
from app.languages.registry import get_language_registry


@pytest.fixture
def router():
    r = get_intent_router()
    r.reset_context()
    return r


def test_interaction_context_numbered_selection():
    ctx = InteractionContext()
    ctx.set_pending_selection(
        intent_name=INTENT_PLAY_MUSIC,
        candidates=["Song A.mp3", "Song B.mp3", "Song C.mp3"],
        entities={"artist": "Artist"},
        language="fa",
    )

    assert ctx.awaiting_selection is True

    # User replies with option "2"
    action, payload = ctx.evaluate_turn("2")
    assert action == "SELECT"
    target_intent, selected_item, entities = payload
    assert target_intent == INTENT_PLAY_MUSIC
    assert selected_item == "Song B.mp3"
    assert entities.get("song") == "Song B.mp3"
    assert ctx.awaiting_selection is False


def test_interaction_context_ordinal_selection():
    ctx = InteractionContext()
    ctx.set_pending_selection(
        intent_name=INTENT_PLAY_MUSIC,
        candidates=["Track 1.wav", "Track 2.wav"],
        language="fa",
    )

    # Persian ordinal 'اول' (first)
    action, payload = ctx.evaluate_turn("اول")
    assert action == "SELECT"
    assert payload[1] == "Track 1.wav"

    # English ordinal 'second'
    ctx.set_pending_selection(
        intent_name=INTENT_PLAY_MUSIC,
        candidates=["Track 1.wav", "Track 2.wav"],
        language="en",
    )
    action2, payload2 = ctx.evaluate_turn("second")
    assert action2 == "SELECT"
    assert payload2[1] == "Track 2.wav"


def test_interaction_context_confirmation_and_cancellation():
    ctx = InteractionContext()
    test_intent = Intent(name="SHUTDOWN", confidence=1.0, language="fa")

    # 1. Confirmation with Persian 'بله'
    ctx.set_pending_confirmation(intent=test_intent, action_label="خاموش کردن سیستم", language="fa")
    assert ctx.awaiting_confirmation is True
    action, payload = ctx.evaluate_turn("بله")
    assert action == "CONFIRM"
    assert payload.name == "SHUTDOWN"
    assert ctx.awaiting_confirmation is False

    # 2. Cancellation with English 'cancel'
    ctx.set_pending_confirmation(intent=test_intent, action_label="shutdown", language="en")
    action_cancel, _ = ctx.evaluate_turn("cancel")
    assert action_cancel == "CANCEL"
    assert ctx.awaiting_confirmation is False


def test_cancellation_in_router(router):
    # Establish pending selection manually
    router.interaction_context.set_pending_selection(
        intent_name=INTENT_PLAY_MUSIC,
        candidates=["Song1.mp3", "Song2.mp3"],
        language="fa",
    )

    out = router.process("کنسل")
    assert out.intent.name == INTENT_CANCEL
    assert "لغو" in out.response_text or "cancelled" in out.response_text.lower()


def test_response_engine_natural_responses():
    engine = get_response_engine()

    intent_fa = Intent(name=INTENT_OPEN_APPLICATION, confidence=1.0, language="fa")
    res_fa = ExecutionResult(
        success=True,
        executed=True,
        status=STATUS_SUCCESS,
        message_key="app_opened",
        params={"app_name": "فایرفاکس"},
    )
    resp = engine.generate(res_fa, intent_fa)
    assert "فایرفاکس" in resp
    assert "باز شد" in resp
