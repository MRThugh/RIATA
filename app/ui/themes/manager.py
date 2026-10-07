"""
Theme Manager for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Centralized theme management supporting runtime dark/light mode switching.
"""

from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.ui.themes.base import ThemeColors
from app.ui.themes.dark import DARK_THEME
from app.ui.themes.light import LIGHT_THEME


class ThemeManager(QObject):
    """Manages active application theme and produces tailored Qt stylesheets."""

    theme_changed = Signal(object)  # Emits current ThemeColors

    def __init__(self, default_theme: str = "dark") -> None:
        super().__init__()
        self._current_name = default_theme
        self._colors: ThemeColors = DARK_THEME if default_theme == "dark" else LIGHT_THEME

    @property
    def current_name(self) -> str:
        return self._current_name

    @property
    def colors(self) -> ThemeColors:
        return self._colors

    @property
    def is_dark(self) -> bool:
        return self._current_name == "dark"

    def set_theme(self, name: str) -> None:
        """Switch current theme between 'dark' and 'light'."""
        if name not in ("dark", "light"):
            return
        if name != self._current_name:
            self._current_name = name
            self._colors = DARK_THEME if name == "dark" else LIGHT_THEME
            self.theme_changed.emit(self._colors)

    def toggle_theme(self) -> str:
        """Toggle between dark and light themes."""
        new_theme = "light" if self._current_name == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme

    def generate_stylesheet(self) -> str:
        """Produce clean, complete Qt stylesheet for current palette."""
        c = self._colors
        return f"""
QMainWindow {{
    background-color: {c.bg_primary};
}}

QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Vazirmatn", "IRANSans", Ubuntu, Cantarell, "Helvetica Neue", Arial, sans-serif;
    color: {c.text_primary};
    background: transparent;
}}

/* Sidebar */
#sidebarWidget {{
    background-color: {c.bg_secondary};
    border-right: 1px solid {c.border_subtle};
}}

#sidebarHeader {{
    padding: 16px 14px;
    border-bottom: 1px solid {c.border_subtle};
}}

#sidebarLogo {{
    font-size: 17px;
    font-weight: 800;
    color: {c.accent_primary};
    letter-spacing: 0.8px;
}}

#sidebarBadge {{
    background-color: {c.bg_elevated};
    color: {c.text_secondary};
    border: 1px solid {c.border_muted};
    border-radius: 5px;
    padding: 2px 6px;
    font-size: 10px;
    font-family: monospace;
}}

#newChatBtn {{
    background-color: {c.accent_primary};
    color: {c.bubble_user_text};
    border: none;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 12px;
    font-weight: 600;
}}

#newChatBtn:hover {{
    background-color: {c.accent_hover};
}}

#newChatBtn:pressed {{
    background-color: {c.accent_active};
}}

/* Conversation items in sidebar */
#convItem {{
    border-radius: 8px;
    padding: 8px 10px;
    background-color: transparent;
    border: 1px solid transparent;
}}

#convItem:hover {{
    background-color: {c.bg_hover};
    border-color: {c.border_subtle};
}}

#convItemActive {{
    border-radius: 8px;
    padding: 8px 10px;
    background-color: {c.bg_surface};
    border: 1px solid {c.border_muted};
}}

#convItemTitle {{
    font-size: 12px;
    font-weight: 600;
    color: {c.text_primary};
}}

#convItemSubtitle {{
    font-size: 10px;
    color: {c.text_muted};
}}

/* Header Bar */
#headerWidget {{
    background-color: {c.bg_secondary};
    border-bottom: 1px solid {c.border_subtle};
    padding: 8px 16px;
}}

#headerTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {c.text_primary};
}}

#headerSubtitle {{
    font-size: 11px;
    color: {c.text_secondary};
}}

#statusDot {{
    color: {c.status_online};
    font-size: 12px;
    font-weight: bold;
}}

#statusText {{
    color: {c.status_online};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

#dryRunBadge {{
    background-color: {c.status_dry_run_bg};
    color: {c.status_dry_run_text};
    border: 1px solid {c.status_dry_run_border};
    border-radius: 5px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
}}

#actionIconButton {{
    background-color: {c.bg_surface};
    color: {c.text_secondary};
    border: 1px solid {c.border_subtle};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 500;
}}

#actionIconButton:hover {{
    background-color: {c.bg_hover};
    color: {c.text_primary};
    border-color: {c.border_muted};
}}

#actionIconButton:pressed {{
    background-color: {c.bg_elevated};
}}

/* Chat scroll area */
QScrollArea {{
    background-color: {c.bg_primary};
    border: none;
}}

#chatScrollContent {{
    background-color: {c.bg_primary};
}}

QScrollBar:vertical {{
    border: none;
    background: {c.scrollbar_track};
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {c.scrollbar_thumb};
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c.scrollbar_thumb_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Message Bubbles */
#userMessageBubble {{
    background-color: {c.bubble_user};
    border: 1px solid {c.bubble_user_border};
    border-radius: 14px;
    padding: 10px 14px;
}}

#userMessageText {{
    color: {c.bubble_user_text};
    font-size: 13px;
    line-height: 1.45;
}}

#assistantMessageBubble {{
    background-color: {c.bubble_assistant};
    border: 1px solid {c.bubble_assistant_border};
    border-radius: 14px;
    padding: 12px 16px;
}}

#assistantMessageText {{
    color: {c.bubble_assistant_text};
    font-size: 13px;
    line-height: 1.5;
}}

#assistantHeader {{
    color: {c.accent_primary};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

#intentBadge {{
    background-color: {c.bubble_badge_bg};
    border: 1px solid {c.border_muted};
    color: {c.bubble_badge_text};
    border-radius: 5px;
    padding: 2px 7px;
    font-size: 10px;
    font-family: monospace;
    font-weight: 600;
}}

#timestampLabel {{
    color: {c.text_muted};
    font-size: 10px;
}}

/* Typing Indicator */
#typingIndicatorWidget {{
    background-color: {c.bubble_assistant};
    border: 1px solid {c.bubble_assistant_border};
    border-radius: 12px;
    padding: 8px 14px;
}}

#typingText {{
    color: {c.text_secondary};
    font-size: 11px;
    font-weight: 500;
}}

#typingDots {{
    color: {c.accent_primary};
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 2px;
}}

/* Input Area Composer */
#inputAreaWidget {{
    background-color: {c.bg_secondary};
    border-top: 1px solid {c.border_subtle};
    padding: 10px 16px 14px 16px;
}}

#inputBoxContainer {{
    background-color: {c.input_bg};
    border: 1px solid {c.input_border};
    border-radius: 10px;
    padding: 4px;
}}

#inputBoxContainer:focus-within {{
    border: 1px solid {c.input_focus_border};
}}

#messageInput {{
    background: transparent;
    color: {c.text_primary};
    border: none;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {c.accent_primary};
}}

#sendButton {{
    background-color: {c.accent_primary};
    color: {c.bubble_user_text};
    border: none;
    border-radius: 7px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
}}

#sendButton:hover {{
    background-color: {c.accent_hover};
}}

#sendButton:pressed {{
    background-color: {c.accent_active};
}}

#sendButton:disabled {{
    background-color: {c.bg_elevated};
    color: {c.text_muted};
}}

/* Quick suggestion chips */
#chipButton {{
    background-color: {c.bg_surface};
    color: {c.text_secondary};
    border: 1px solid {c.border_subtle};
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 500;
}}

#chipButton:hover {{
    background-color: {c.bg_hover};
    color: {c.text_primary};
    border-color: {c.border_muted};
}}

/* Dialogs */
QDialog {{
    background-color: {c.bg_secondary};
    color: {c.text_primary};
}}
"""


_GLOBAL_THEME_MANAGER: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Retrieve global ThemeManager singleton."""
    global _GLOBAL_THEME_MANAGER
    if _GLOBAL_THEME_MANAGER is None:
        _GLOBAL_THEME_MANAGER = ThemeManager()
    return _GLOBAL_THEME_MANAGER
