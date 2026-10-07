"""
Automated unit & regression tests for R.I.A.T.A v0.1.1 PySide6 Desktop UI.
Author: Ali Kamrani (MRThugh)

Verifies:
- MainWindow lifecycle in offscreen mode
- Conversational chat area and message widgets
- Language toggling & RTL/LTR dynamic layout switching
- Live Dark/Light theme switching
- Multi-session chat thread management
"""

import sys
import pytest

# Ensure PySide6 and Qt platform runtime are available before importing widgets
pytest.importorskip("PySide6")
try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
except Exception as err:
    pytest.skip(f"PySide6 Qt platform runtime not available: {err}", allow_module_level=True)

from app.ui.chat.chat_view import ChatView
from app.ui.input.message_input import MessageInputWidget
from app.ui.main_window import MainWindow
from app.ui.themes.manager import get_theme_manager


@pytest.fixture(scope="session")
def qapp():
    """Ensure a singleton QApplication exists in offscreen mode for test runner."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["riata_test", "-platform", "offscreen"])
    return app


def test_theme_manager_switching():
    tm = get_theme_manager()
    initial_theme = tm.current_name

    # Switch to light
    tm.set_theme("light")
    assert tm.current_name == "light"
    assert tm.colors.bg_primary == "#f8fafc"
    light_css = tm.generate_stylesheet()
    assert "#f8fafc" in light_css

    # Switch to dark
    tm.set_theme("dark")
    assert tm.current_name == "dark"
    assert tm.colors.bg_primary == "#0b0f19"
    dark_css = tm.generate_stylesheet()
    assert "#0b0f19" in dark_css


def test_chat_view_components(qapp):
    cv = ChatView()

    # Add user message
    user_msg = cv.add_message("Open Firefox", is_user=True, direction="ltr", animate=False)
    assert user_msg.is_user is True
    assert user_msg.direction == "ltr"

    # Add assistant message
    asst_msg = cv.add_message("Opening Firefox...", is_user=False, intent_name="OPEN_APPLICATION", direction="ltr", animate=False)
    assert asst_msg.is_user is False

    # Typing indicator toggle
    cv.set_typing(True, "Working...")
    assert cv.typing_indicator.is_active is True
    assert cv.typing_indicator.isHidden() is False

    cv.set_typing(False)
    assert cv.typing_indicator.is_active is False
    assert cv.typing_indicator.isHidden() is True

    # Clear
    cv.clear_messages()
    assert cv.layout.count() >= 2


def test_message_input_composer(qapp):
    inp = MessageInputWidget()
    assert inp.text_edit is not None

    inp.set_placeholder("Test placeholder")
    assert inp.text_edit.placeholderText() == "Test placeholder"

    inp.set_enabled_state(False)
    assert inp.text_edit.isEnabled() is False
    assert inp.send_btn.isEnabled() is False

    inp.set_enabled_state(True)
    assert inp.text_edit.isEnabled() is True
    assert inp.send_btn.isEnabled() is True


def test_main_window_lifecycle_and_multilingual(qapp):
    window = MainWindow()

    # Initial Persian RTL layout
    assert window.layoutDirection() == Qt.LayoutDirection.RightToLeft

    # Toggle to English LTR
    window._toggle_language()
    assert window.layoutDirection() == Qt.LayoutDirection.LeftToRight
    assert window._current_language == "en"

    # Toggle back to Persian RTL
    window._toggle_language()
    assert window.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert window._current_language == "fa"

    # Live theme toggling
    initial_theme = window.theme_manager.current_name
    window._toggle_theme()
    assert window.theme_manager.current_name != initial_theme
    window._toggle_theme()
    assert window.theme_manager.current_name == initial_theme

    # Session management
    assert window._active_session_id == "default"
    window._create_new_chat()
    assert window._active_session_id == "session_2"

    window._switch_session("default")
    assert window._active_session_id == "default"

    # Clear active chat
    window._clear_chat()
    assert len(window._session_histories["default"]) == 0
