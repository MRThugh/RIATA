"""
Unit tests for Intent Matcher in R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import pytest
from app.core.constants import INTENT_OPEN_APPLICATION
from app.engine.matcher import RuleBasedIntentParser, get_intent_parser


@pytest.fixture
def parser() -> RuleBasedIntentParser:
    return get_intent_parser()


def test_persian_open_application_variations(parser: RuleBasedIntentParser) -> None:
    variations = [
        "فایرفاکس رو باز کن",
        "فایرفاکس را باز کن",
        "فایرفاکس باز کن",
        "فایرفاکس رو اجرا کن",
        "لطفا فایرفاکس رو باز کن",
        "لطفاً فایرفاکس رو باز کن",
        "Firefox رو باز کن",
    ]

    for phrase in variations:
        intent = parser.parse(phrase)
        assert intent.name == INTENT_OPEN_APPLICATION, f"Failed for phrase: '{phrase}'"
        assert intent.entities.get("application") == "firefox", f"Entity mismatch for: '{phrase}'"
        assert intent.confidence >= 0.80


def test_english_open_application_variations(parser: RuleBasedIntentParser) -> None:
    variations = [
        "open firefox",
        "launch firefox",
        "start firefox",
        "run firefox",
        "please open firefox",
        "can you open firefox",
        "can you please open firefox",
        "Open Firefox",
    ]

    for phrase in variations:
        intent = parser.parse(phrase)
        assert intent.name == INTENT_OPEN_APPLICATION, f"Failed for phrase: '{phrase}'"
        assert intent.entities.get("application") == "firefox", f"Entity mismatch for: '{phrase}'"
        assert intent.confidence >= 0.80
