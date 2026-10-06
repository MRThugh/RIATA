"""
Unit tests for Normalizer in R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import pytest
from app.core.constants import LANG_ENGLISH, LANG_PERSIAN
from app.engine.normalizer import Normalizer, get_normalizer


@pytest.fixture
def normalizer() -> Normalizer:
    return get_normalizer()


def test_persian_character_normalization(normalizer: Normalizer) -> None:
    # Arabic Yeh to Persian Yeh (ي -> ی)
    assert "فایرفاکس" in normalizer.normalize("فايرفاكس", LANG_PERSIAN)

    # Arabic Kaf to Persian Kaf (ك -> ک)
    assert normalizer.normalize("كتاب", LANG_PERSIAN) == "کتاب"

    # Arabic Teh Marbuta and Heh variations
    assert "نامه" in normalizer.normalize("نامة", LANG_PERSIAN)


def test_persian_whitespace_and_spacing(normalizer: Normalizer) -> None:
    # Multiple spaces
    raw = "  فایرفاکس    رو     باز   کن   "
    normalized = normalizer.normalize(raw, LANG_PERSIAN)
    assert normalized == "فایرفاکس رو باز کن"

    # ZWNJ conversion
    raw_zwnj = "می\u200cخوام"
    assert "می" in normalizer.normalize(raw_zwnj, LANG_PERSIAN)


def test_persian_digits_normalization(normalizer: Normalizer) -> None:
    assert normalizer.normalize("۱۲۳۴۵", LANG_PERSIAN) == "12345"
    assert normalizer.normalize("١٢٣٤٥", LANG_PERSIAN) == "12345"


def test_persian_particles_stripping(normalizer: Normalizer) -> None:
    text = "لطفا فایرفاکس رو باز کن"
    stripped = normalizer.strip_conversational_particles(text, LANG_PERSIAN)
    assert stripped == "فایرفاکس رو باز کن"

    text2 = "میشه فایرفاکس رو باز کن"
    stripped2 = normalizer.strip_conversational_particles(text2, LANG_PERSIAN)
    assert stripped2 == "فایرفاکس رو باز کن"


def test_english_normalization(normalizer: Normalizer) -> None:
    assert normalizer.normalize("  Open   Firefox!  ", LANG_ENGLISH) == "open firefox"
    assert normalizer.normalize("What's up?", LANG_ENGLISH) == "what is up"


def test_english_particles_stripping(normalizer: Normalizer) -> None:
    text = "please open firefox"
    stripped = normalizer.strip_conversational_particles(text, LANG_ENGLISH)
    assert stripped == "open firefox"

    text2 = "can you please open firefox"
    stripped2 = normalizer.strip_conversational_particles(text2, LANG_ENGLISH)
    assert stripped2 == "open firefox"
