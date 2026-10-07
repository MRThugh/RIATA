"""
Unit tests for R.I.A.T.A v0.2.0 Context Engine.
Author: Ali Kamrani (MRThugh)

Verifies:
- SessionContext creation, updates, and resets
- Active entities tracking (application, directory, file)
- Session isolation between distinct session IDs
- Bounded history memory ring buffer
- Confirmation token binding, expiration, and non-replayability
"""

import time
import pytest

from app.core.context.manager import ContextManager, get_context_manager
from app.core.context.models import PendingConfirmation, SessionContext
from app.engine.intent import Intent
from app.executor.result import STATUS_SUCCESS, ExecutionResult


def test_session_context_creation_and_attributes():
    ctx = SessionContext(session_id="test-session-1")
    assert ctx.session_id == "test-session-1"
    assert ctx.active_application is None
    assert ctx.active_directory is None
    assert ctx.active_file is None
    assert ctx.conversation_turn == 0
    assert len(ctx.history) == 0


def test_session_context_record_turn_and_updates():
    ctx = SessionContext(session_id="test-session-2")

    # Turn 1: Open Application
    intent1 = Intent(
        name="OPEN_APPLICATION",
        confidence=1.0,
        entities={"application": "firefox"},
        raw_text="Open Firefox",
    )
    res1 = ExecutionResult(
        success=True,
        executed=True,
        status=STATUS_SUCCESS,
        intent_name="OPEN_APPLICATION",
    )
    ctx.record_turn(intent1, res1)

    assert ctx.conversation_turn == 1
    assert ctx.active_application == "firefox"
    assert "firefox" in ctx.open_applications
    assert ctx.current_intent == intent1

    # Turn 2: Open Directory
    intent2 = Intent(
        name="OPEN_FOLDER",
        confidence=1.0,
        entities={"folder": "Downloads"},
        raw_text="Open Downloads",
    )
    res2 = ExecutionResult(
        success=True,
        executed=True,
        status=STATUS_SUCCESS,
        intent_name="OPEN_FOLDER",
    )
    ctx.record_turn(intent2, res2)

    assert ctx.conversation_turn == 2
    assert ctx.active_directory == "Downloads"
    assert ctx.active_application == "firefox"  # Preserved
    assert ctx.previous_intent == intent1
    assert ctx.current_intent == intent2

    # Turn 3: Create File
    intent3 = Intent(
        name="CREATE_FILE",
        confidence=1.0,
        entities={"file": "notes.txt"},
        raw_text="Create notes.txt in it",
    )
    res3 = ExecutionResult(
        success=True,
        executed=True,
        status=STATUS_SUCCESS,
        intent_name="CREATE_FILE",
    )
    ctx.record_turn(intent3, res3)

    assert ctx.active_file == "notes.txt"
    assert ctx.active_directory == "Downloads"


def test_session_context_bounded_history():
    ctx = SessionContext(session_id="test-session-history")
    intent = Intent(name="SHOW_SYSTEM_INFO", confidence=1.0)
    res = ExecutionResult(success=True, executed=True, status=STATUS_SUCCESS)

    # Record 30 turns with max_history=10
    for i in range(30):
        ctx.record_turn(intent, res, max_history=10)

    assert ctx.conversation_turn == 30
    assert len(ctx.history) == 10
    assert ctx.history[-1]["turn"] == 30
    assert ctx.history[0]["turn"] == 21


def test_session_context_clear_reset():
    ctx = SessionContext(session_id="test-reset")
    intent = Intent(name="OPEN_APPLICATION", confidence=1.0, entities={"application": "firefox"})
    res = ExecutionResult(success=True, executed=True, status=STATUS_SUCCESS)
    ctx.record_turn(intent, res)

    assert ctx.active_application == "firefox"
    ctx.clear()

    assert ctx.active_application is None
    assert ctx.active_directory is None
    assert ctx.active_file is None
    assert ctx.current_intent is None
    assert len(ctx.history) == 0


def test_context_manager_session_isolation():
    manager = ContextManager()

    s1 = manager.get_or_create("user-desktop")
    s2 = manager.get_or_create("user-web-1")

    # Mutate session 1
    intent = Intent(name="OPEN_APPLICATION", confidence=1.0, entities={"application": "chrome"})
    res = ExecutionResult(success=True, executed=True, status=STATUS_SUCCESS)
    s1.record_turn(intent, res)

    assert s1.active_application == "chrome"
    assert s2.active_application is None  # Web session is isolated!


def test_pending_confirmation_lifecycle_and_non_replayability():
    manager = ContextManager()
    intent = Intent(name="DELETE_FILE", confidence=1.0, entities={"file": "temp.txt"})

    # Create confirmation token
    conf = manager.set_pending_confirmation("session-conf-1", intent, action_label="delete temp.txt", ttl=10.0)
    assert conf.is_valid() is True
    assert conf.status == "PENDING"
    assert conf.action == "DELETE_FILE"

    # Consume token
    retrieved = manager.consume_pending_confirmation("session-conf-1", conf.confirmation_id)
    assert retrieved is not None
    assert retrieved.name == "DELETE_FILE"
    assert conf.status == "CONSUMED"

    # Replay attempt: must return None!
    replayed = manager.consume_pending_confirmation("session-conf-1", conf.confirmation_id)
    assert replayed is None


def test_pending_confirmation_expiration():
    manager = ContextManager()
    intent = Intent(name="DELETE_FILE", confidence=1.0, entities={"file": "temp.txt"})

    # Set with immediate expiry
    conf = manager.set_pending_confirmation("session-exp", intent, action_label="delete", ttl=0.01)
    time.sleep(0.02)

    assert conf.is_valid() is False
    consumed = manager.consume_pending_confirmation("session-exp")
    assert consumed is None
