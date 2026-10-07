"""
Conversation Session Item for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Sidebar list item representing an active or past conversation session.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class ConversationItemWidget(QWidget):
    """Clickable sidebar item representing a conversation thread."""

    clicked = Signal(str)  # Emits session_id

    def __init__(
        self,
        session_id: str,
        title: str,
        subtitle: str = "",
        is_active: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.session_id = session_id
        self._title = title
        self._subtitle = subtitle
        self._is_active = is_active

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("convItemActive" if self._is_active else "convItem")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # Icon / bullet
        icon_label = QLabel("💬")
        icon_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(icon_label)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel(self._title)
        self.title_label.setObjectName("convItemTitle")
        text_layout.addWidget(self.title_label)

        if self._subtitle:
            self.sub_label = QLabel(self._subtitle)
            self.sub_label.setObjectName("convItemSubtitle")
            text_layout.addWidget(self.sub_label)

        layout.addLayout(text_layout)
        layout.addStretch()

    def set_active(self, active: bool) -> None:
        """Update active visual selection state."""
        self._is_active = active
        self.setObjectName("convItemActive" if active else "convItem")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.session_id)
        super().mousePressEvent(event)
