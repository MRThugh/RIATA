"""
Header Bar for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Top application shell header with conversation title, sidebar toggle, and quick actions.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class HeaderBarWidget(QWidget):
    """Modern header bar above chat timeline."""

    toggle_sidebar_requested = Signal()
    clear_chat_requested = Signal()
    theme_toggled = Signal()
    language_toggled = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("headerWidget")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # 1. Sidebar toggle button
        self.sidebar_toggle_btn = QPushButton("☰", self)
        self.sidebar_toggle_btn.setObjectName("actionIconButton")
        self.sidebar_toggle_btn.setFixedSize(32, 32)
        self.sidebar_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_btn.setToolTip("Toggle Sidebar / تغییر نوار کناری")
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar_requested.emit)
        layout.addWidget(self.sidebar_toggle_btn)

        # 2. Conversation Info Column
        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        self.title_label = QLabel("R.I.A.T.A Conversation", self)
        self.title_label.setObjectName("headerTitle")
        title_col.addWidget(self.title_label)

        self.subtitle_label = QLabel("Deterministic Desktop Interaction Assistant", self)
        self.subtitle_label.setObjectName("headerSubtitle")
        title_col.addWidget(self.subtitle_label)

        layout.addLayout(title_col)
        layout.addStretch()

        # 3. Action Buttons
        self.clear_btn = QPushButton("🗑 Clear / پاک کردن", self)
        self.clear_btn.setObjectName("actionIconButton")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_chat_requested.emit)
        layout.addWidget(self.clear_btn)

        self.lang_btn = QPushButton("🌐 FA / EN", self)
        self.lang_btn.setObjectName("actionIconButton")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.clicked.connect(self.language_toggled.emit)
        layout.addWidget(self.lang_btn)

        self.theme_btn = QPushButton("🌓", self)
        self.theme_btn.setObjectName("actionIconButton")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("Toggle Theme (Dark / Light)")
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        layout.addWidget(self.theme_btn)

    def set_conversation_title(self, title: str, subtitle: str = "") -> None:
        """Update header labels for active conversation."""
        self.title_label.setText(title)
        if subtitle:
            self.subtitle_label.setText(subtitle)
