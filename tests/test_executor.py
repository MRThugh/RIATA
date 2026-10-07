"""
Unit tests for safe execution, safety checks, and dry-run mode in R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

import pytest
from app.core.config import get_config
from app.core.constants import (
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FOLDER,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_UNKNOWN,
)
from app.engine.router import get_intent_router
from app.executor.files import resolve_folder_path


@pytest.fixture
def router():
    return get_intent_router()


def test_dangerous_commands_blocked(router):
    dangerous_inputs = [
        "sudo rm -rf /",
        "rm -rf ~",
        "mkfs /dev/sda",
        "shutdown now",
        "reboot",
        ":(){ :|:& };:",
    ]

    for cmd in dangerous_inputs:
        output = router.process(cmd)
        # Must be flagged as dangerous and NOT executed
        assert output.intent.is_dangerous is True
        assert output.intent.is_actionable is False
        assert output.result is not None
        assert output.result.success is False
        # Must include security warning
        assert "امنیت" in output.response_text or "security" in output.response_text.lower()


def test_dry_run_mode(router):
    config = get_config()
    config.dry_run = True

    try:
        output = router.process("Open Firefox")
        assert output.intent.name == INTENT_OPEN_APPLICATION
        if output.result.success:
            assert output.result.is_dry_run is True
            assert "DRY RUN" in output.response_text or "حالت آزمایشی" in output.response_text
    finally:
        config.dry_run = False


def test_folder_resolution_safety():
    # Canonical user directories
    downloads = resolve_folder_path("Downloads")
    assert downloads is not None
    assert "Downloads" in str(downloads)

    # Disallow dangerous root paths
    assert resolve_folder_path("/etc") is None
    assert resolve_folder_path("../../../etc") is None


def test_system_info_execution(router):
    output = router.process("مشخصات سیستم")
    assert output.intent.name == INTENT_SHOW_SYSTEM_INFO
    assert output.result.success is True
    assert "سیستم‌عامل" in output.response_text or "OS" in output.response_text
    assert "کرنل" in output.response_text or "Kernel" in output.response_text


def test_unknown_command_does_not_execute(router):
    output = router.process("some non-existent gibberish command")
    assert output.intent.name == INTENT_UNKNOWN
    assert output.result.success is False


def test_music_multiple_matches_and_context(tmp_path, router):
    config = get_config()
    orig_music_dir = config.music_directory
    config.music_directory = str(tmp_path)
    config.dry_run = True

    try:
        # Create multiple matching audio files
        (tmp_path / "Another Love.mp3").write_text("audio")
        (tmp_path / "Another Love Live.mp3").write_text("audio")
        (tmp_path / "Another Love Remix.wav").write_text("audio")

        # Step 1: User requests "play Another Love" -> multiple matches returned
        out1 = router.process("آهنگ Another Love رو پخش کن")
        assert out1.result.requires_context is True
        assert "3 آهنگ پیدا کردم" in out1.response_text or "Another Love" in out1.response_text

        # Step 2: Context retains candidates, user selects option "1"
        out2 = router.process("1")
        assert out2.result.success is True
        assert out2.result.is_dry_run is True
        assert "Another Love" in out2.response_text
    finally:
        config.music_directory = orig_music_dir
        config.dry_run = False

