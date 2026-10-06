"""
Unit tests for Entity Extractor in R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import pytest
from app.core.constants import (
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FOLDER,
    INTENT_PLAY_MUSIC,
    LANG_ENGLISH,
    LANG_PERSIAN,
)
from app.engine.entity_extractor import get_entity_extractor


@pytest.fixture
def extractor():
    return get_entity_extractor()


def test_application_extraction(extractor):
    res_fa = extractor.extract(
        INTENT_OPEN_APPLICATION,
        "فایرفاکس رو باز کن",
        LANG_PERSIAN,
        raw_text="فایرفاکس رو باز کن",
    )
    assert res_fa.get("application") == "firefox"

    res_en = extractor.extract(
        INTENT_OPEN_APPLICATION,
        "open firefox",
        LANG_ENGLISH,
        raw_text="open firefox",
    )
    assert res_en.get("application") == "firefox"


def test_folder_extraction(extractor):
    res_fa = extractor.extract(
        INTENT_OPEN_FOLDER,
        "پوشه دانلودها رو باز کن",
        LANG_PERSIAN,
    )
    assert res_fa.get("folder") == "Downloads"

    res_en = extractor.extract(
        INTENT_OPEN_FOLDER,
        "open downloads",
        LANG_ENGLISH,
    )
    assert res_en.get("folder") == "Downloads"


def test_song_extraction(extractor):
    res_fa = extractor.extract(
        INTENT_PLAY_MUSIC,
        "اهنگ another love رو پخش کن",
        LANG_PERSIAN,
        raw_text="آهنگ Another Love رو پخش کن",
    )
    assert res_fa.get("song") == "Another Love"

    res_en = extractor.extract(
        INTENT_PLAY_MUSIC,
        "play another love",
        LANG_ENGLISH,
        raw_text="play Another Love",
    )
    assert res_en.get("song") == "Another Love"
