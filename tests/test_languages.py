"""
Unit tests for Language Loader and Detector in R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import pytest
from app.core.constants import LANG_ENGLISH, LANG_PERSIAN
from app.languages.detector import detect_language, get_language_detector
from app.languages.loader import get_language_loader


def test_language_detection():
    detector = get_language_detector()

    # Persian input with English app name
    assert detector.detect("Firefox رو باز کن") == LANG_PERSIAN

    # Pure Persian
    assert detector.detect("فایرفاکس را باز کن") == LANG_PERSIAN
    assert detector.detect("آهنگ پخش کن") == LANG_PERSIAN

    # English input
    assert detector.detect("Open Firefox") == LANG_ENGLISH
    assert detector.detect("play Another Love") == LANG_ENGLISH
    assert detector.detect("show system info") == LANG_ENGLISH


def test_language_pack_loader():
    loader = get_language_loader()

    # Verify Persian pack
    fa_pack = loader.get_pack(LANG_PERSIAN)
    assert fa_pack.code == "fa"
    assert fa_pack.direction == "rtl"
    assert "greeting" in fa_pack.responses
    assert "OPEN_APPLICATION" in fa_pack.intents

    # Verify English pack
    en_pack = loader.get_pack(LANG_ENGLISH)
    assert en_pack.code == "en"
    assert en_pack.direction == "ltr"
    assert "greeting" in en_pack.responses
    assert "OPEN_APPLICATION" in en_pack.intents


def test_independent_language_packs():
    loader = get_language_loader()
    available = [item[0] for item in loader.get_available_languages()]
    assert "fa" in available
    assert "en" in available
