"""
Unit tests for R.I.A.T.A v0.2.0 Contextual Entity Resolution & Ambiguity Handling.
Author: Ali Kamrani (MRThugh)

Verifies:
- Explicit entity recognition
- Persian pronoun suffix resolution ('ببندش' -> active application)
- Persian locative container resolution ('داخلش فایل test.txt رو بساز' -> active directory)
- English pronoun resolution ('close it' -> active application)
- English locative container resolution ('create test.txt in it' -> active directory)
- Ambiguity detection when multiple candidates are active
- Asking for clarification instead of guessing dangerous targets
"""

import pytest

from app.core.context.models import SessionContext
from app.core.context.resolver import ContextualEntityResolver


def test_explicit_entity_overrides_context():
    resolver = ContextualEntityResolver()
    ctx = SessionContext(session_id="res-1")
    ctx.active_application = "firefox"

    # User explicitly mentions chrome
    res = resolver.resolve(
        raw_text="Chrome رو ببند",
        parsed_intent_name="CLOSE_APPLICATION",
        extracted_entities={"application": "chrome"},
        context=ctx,
        language="fa",
    )
    assert res.resolved is True
    assert res.entities["application"] == "chrome"
    assert res.is_ambiguous is False


def test_persian_pronoun_resolution_single_active_app():
    resolver = ContextualEntityResolver()
    ctx = SessionContext(session_id="res-2")
    ctx.active_application = "Firefox"
    ctx.open_applications = ["Firefox"]

    # User says "ببندش"
    res = resolver.resolve(
        raw_text="ببندش",
        parsed_intent_name="CLOSE_APPLICATION",
        extracted_entities={},
        context=ctx,
        language="fa",
    )
    assert res.resolved is True
    assert res.entities["application"] == "Firefox"
    assert res.is_ambiguous is False


def test_english_pronoun_resolution_single_active_app():
    resolver = ContextualEntityResolver()
    ctx = SessionContext(session_id="res-3")
    ctx.active_application = "Firefox"
    ctx.open_applications = ["Firefox"]

    # User says "close it"
    res = resolver.resolve(
        raw_text="close it",
        parsed_intent_name="CLOSE_APPLICATION",
        extracted_entities={},
        context=ctx,
        language="en",
    )
    assert res.resolved is True
    assert res.entities["application"] == "Firefox"
    assert res.is_ambiguous is False


def test_persian_locative_container_resolution():
    resolver = ContextualEntityResolver()
    ctx = SessionContext(session_id="res-4")
    ctx.active_directory = "Downloads"

    # User says "داخلش فایل test.txt رو بساز"
    res = resolver.resolve(
        raw_text="داخلش فایل test.txt رو بساز",
        parsed_intent_name="CREATE_FILE",
        extracted_entities={"file": "test.txt"},
        context=ctx,
        language="fa",
    )
    assert res.resolved is True
    assert res.entities["file"] == "test.txt"
    assert res.entities["folder"] == "Downloads"


def test_english_locative_container_resolution():
    resolver = ContextualEntityResolver()
    ctx = SessionContext(session_id="res-5")
    ctx.active_directory = "Documents"

    # User says "create test.txt in it"
    res = resolver.resolve(
        raw_text="create test.txt in it",
        parsed_intent_name="CREATE_FILE",
        extracted_entities={"file": "test.txt"},
        context=ctx,
        language="en",
    )
    assert res.resolved is True
    assert res.entities["file"] == "test.txt"
    assert res.entities["folder"] == "Documents"


def test_ambiguity_detection_multiple_candidates_persian():
    resolver = ContextualEntityResolver()
    ctx = SessionContext(session_id="res-amb-fa")

    # Step 1: User indicates "Chrome و Firefox باز هستند"
    declared = resolver._detect_open_state_declaration("chrome و firefox باز هستند", "fa")
    assert "Chrome" in declared
    assert "Firefox" in declared
    ctx.open_applications = declared

    # Step 2: User says "ببندش"
    res = resolver.resolve(
        raw_text="ببندش",
        parsed_intent_name="CLOSE_APPLICATION",
        extracted_entities={},
        context=ctx,
        language="fa",
    )
    assert res.resolved is False
    assert res.is_ambiguous is True
    assert len(res.candidates) >= 2
    assert "Chrome" in res.candidates
    assert "Firefox" in res.candidates
    # Prompt asks clarification instead of arbitrarily closing one!
    assert "کدوم برنامه رو ببندم؟" in res.clarification_prompt
    assert "Chrome" in res.clarification_prompt
    assert "Firefox" in res.clarification_prompt


def test_ambiguity_detection_multiple_candidates_english():
    resolver = ContextualEntityResolver()
    ctx = SessionContext(session_id="res-amb-en")

    declared = resolver._detect_open_state_declaration("chrome and firefox are open", "en")
    assert "Chrome" in declared
    assert "Firefox" in declared
    ctx.open_applications = declared

    res = resolver.resolve(
        raw_text="close it",
        parsed_intent_name="CLOSE_APPLICATION",
        extracted_entities={},
        context=ctx,
        language="en",
    )
    assert res.resolved is False
    assert res.is_ambiguous is True
    assert "Which application should I close?" in res.clarification_prompt
