"""
Chat View timeline container for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Features smart non-intrusive auto-scrolling, typing state indicators,
and message bubble lifecycle management.
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.chat.message_widget import MessageWidget
from app.ui.chat.typing_indicator import TypingIndicator


class ChatView(QScrollArea):
    """Scrollable conversation view with smart auto-scroll and typing feedback."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("chatScrollArea")

        self.container = QWidget()
        self.container.setObjectName("chatScrollContent")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 14, 0, 14)
        self.layout.setSpacing(8)

        # Typing indicator sits above bottom stretch
        self.typing_indicator = TypingIndicator(self.container)

        self.layout.addStretch()
        self.layout.addWidget(self.typing_indicator)

        self.setWidget(self.container)

    def add_message(
        self,
        text: str,
        is_user: bool = False,
        intent_name: Optional[str] = None,
        direction: str = "ltr",
        timestamp: Optional[str] = None,
        animate: bool = True,
    ) -> MessageWidget:
        """Add new bubble to the conversation timeline."""
        was_at_bottom = self._is_near_bottom()

        widget = MessageWidget(
            text=text,
            is_user=is_user,
            intent_name=intent_name,
            direction=direction,
            timestamp=timestamp,
            animate=animate,
            parent=self.container,
        )

        # Insert before typing indicator and stretch
        idx = max(0, self.layout.count() - 2)
        self.layout.insertWidget(idx, widget)

        # Smart auto-scroll: user messages always scroll, assistant only if user was at bottom
        if is_user or was_at_bottom:
            QTimer.singleShot(60, self.scroll_to_bottom)

        return widget

    def set_typing(self, is_typing: bool, text: str = "R.I.A.T.A is working...") -> None:
        """Toggle active typing indicator."""
        if is_typing:
            self.typing_indicator.start(text)
            QTimer.singleShot(50, self.scroll_to_bottom)
        else:
            self.typing_indicator.stop()

    def _is_near_bottom(self) -> bool:
        """Check if viewport is close to the bottom (within 80px)."""
        v_bar = self.verticalScrollBar()
        return (v_bar.maximum() - v_bar.value()) <= 80

    def scroll_to_bottom(self) -> None:
        """Smoothly advance scrollbar to bottommost position."""
        v_bar = self.verticalScrollBar()
        v_bar.setValue(v_bar.maximum())

    def clear_messages(self) -> None:
        """Remove all messages while preserving layout stretch and typing indicator."""
        # Remove widgets up to typing indicator
        while self.layout.count() > 2:
            item = self.layout.takeAt(0)
            if item.widget() and item.widget() != self.typing_indicator:
                item.widget().deleteLater()
