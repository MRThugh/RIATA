"""
Scrollable chat timeline container for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.message_widget import MessageWidget


class ChatWidget(QScrollArea):
    """Scrollable conversation container."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setObjectName("scrollContent")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 10, 0, 10)
        self.layout.setSpacing(8)
        self.layout.addStretch()

        self.setWidget(self.container)

    def add_message(
        self,
        text: str,
        is_user: bool = False,
        intent_name: Optional[str] = None,
        direction: str = "ltr",
    ) -> None:
        """Add new bubble to the chat conversation."""
        # Insert before bottom stretch
        count = self.layout.count()
        widget = MessageWidget(
            text=text,
            is_user=is_user,
            intent_name=intent_name,
            direction=direction,
        )
        self.layout.insertWidget(count - 1, widget)

        # Smooth auto-scroll to bottom
        QTimer.singleShot(50, self.scroll_to_bottom)

    def scroll_to_bottom(self) -> None:
        """Scroll vertical scrollbar to bottommost position."""
        v_bar = self.verticalScrollBar()
        v_bar.setValue(v_bar.maximum())

    def clear_messages(self) -> None:
        """Remove all messages from timeline except bottom stretch."""
        while self.layout.count() > 1:
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
