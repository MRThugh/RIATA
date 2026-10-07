"""
Unit tests for all core Intents in R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

import pytest
from app.core.constants import (
    INTENT_CLARIFY,
    INTENT_EXIT_APPLICATION,
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FILE_MANAGER,
    INTENT_OPEN_FOLDER,
    INTENT_OPEN_SETTINGS,
    INTENT_OPEN_TERMINAL,
    INTENT_PLAY_MUSIC,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_TAKE_SCREENSHOT,
    INTENT_UNKNOWN,
)
from app.engine.matcher import get_intent_parser


@pytest.fixture
def parser():
    return get_intent_parser()


def test_open_folder_intents(parser):
    # Persian
    intent_fa = parser.parse("Downloads رو باز کن")
    assert intent_fa.name == INTENT_OPEN_FOLDER
    assert intent_fa.entities.get("folder") == "Downloads"

    intent_fa2 = parser.parse("پوشه اسناد رو باز کن")
    assert intent_fa2.name == INTENT_OPEN_FOLDER
    assert intent_fa2.entities.get("folder") == "Documents"

    # English
    intent_en = parser.parse("open Downloads")
    assert intent_en.name == INTENT_OPEN_FOLDER
    assert intent_en.entities.get("folder") == "Downloads"

    intent_en2 = parser.parse("open my documents folder")
    assert intent_en2.name == INTENT_OPEN_FOLDER
    assert intent_en2.entities.get("folder") == "Documents"


def test_play_music_intents(parser):
    # Persian generic
    intent_fa = parser.parse("اهنگ پخش کن")
    assert intent_fa.name == INTENT_PLAY_MUSIC

    # Persian specific song
    intent_fa_song = parser.parse("آهنگ Another Love رو پخش کن")
    assert intent_fa_song.name == INTENT_PLAY_MUSIC
    assert intent_fa_song.entities.get("song") == "Another Love"

    # English generic
    intent_en = parser.parse("play music")
    assert intent_en.name == INTENT_PLAY_MUSIC

    # English specific song
    intent_en_song = parser.parse("play Another Love")
    assert intent_en_song.name == INTENT_PLAY_MUSIC
    assert intent_en_song.entities.get("song") == "Another Love"


def test_terminal_intents(parser):
    assert parser.parse("ترمینال رو باز کن").name == INTENT_OPEN_TERMINAL
    assert parser.parse("open terminal").name == INTENT_OPEN_TERMINAL
    assert parser.parse("launch terminal").name == INTENT_OPEN_TERMINAL


def test_file_manager_intents(parser):
    assert parser.parse("فایل منیجر رو باز کن").name == INTENT_OPEN_FILE_MANAGER
    assert parser.parse("open file manager").name == INTENT_OPEN_FILE_MANAGER
    assert parser.parse("open files").name == INTENT_OPEN_FILE_MANAGER


def test_settings_intents(parser):
    assert parser.parse("تنظیمات رو باز کن").name == INTENT_OPEN_SETTINGS
    assert parser.parse("open settings").name == INTENT_OPEN_SETTINGS


def test_system_info_intents(parser):
    assert parser.parse("مشخصات سیستم رو نشون بده").name == INTENT_SHOW_SYSTEM_INFO
    assert parser.parse("اطلاعات سیستم").name == INTENT_SHOW_SYSTEM_INFO
    assert parser.parse("show system information").name == INTENT_SHOW_SYSTEM_INFO
    assert parser.parse("system info").name == INTENT_SHOW_SYSTEM_INFO


def test_screenshot_intents(parser):
    assert parser.parse("اسکرین شات بگیر").name == INTENT_TAKE_SCREENSHOT
    assert parser.parse("take a screenshot").name == INTENT_TAKE_SCREENSHOT


def test_exit_intents(parser):
    assert parser.parse("ریاتا رو ببند").name == INTENT_EXIT_APPLICATION
    assert parser.parse("خروج").name == INTENT_EXIT_APPLICATION
    assert parser.parse("exit").name == INTENT_EXIT_APPLICATION
    assert parser.parse("close riata").name == INTENT_EXIT_APPLICATION


def test_unknown_and_clarification_intents(parser):
    # Random nonsense
    intent = parser.parse("xyz random command 12345")
    assert intent.name == INTENT_UNKNOWN

    # Vague requests
    intent_vague_fa = parser.parse("اون رو باز کن")
    assert intent_vague_fa.is_clarification_needed or intent_vague_fa.name == INTENT_CLARIFY

    intent_vague_en = parser.parse("open that")
    assert intent_vague_en.is_clarification_needed or intent_vague_en.name == INTENT_CLARIFY
