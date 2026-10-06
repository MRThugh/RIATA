"""
Message bubble widget for R.I.A.T.A v0.1.0 chat interface
Author: Ali Kamrani (MRThugh)
"""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MessageWidget(QWidget):
    """Visual chat bubble widget for both user and assistant messages."""

    def __init__(
        self,
        text: str,
        is_user: bool = False,
        intent_name: Optional[str] = None,
        direction: str = "ltr",
        timestamp: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.is_user = is_user
        self.direction = direction
        self.time_str = timestamp or datetime.now().strftime("%H:%M")

        self._init_ui(text, intent_name)

    def _init_ui(self, text: str, intent_name: Optional[str]) -> None:
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(16, 6, 16, 6)
        outer_layout.setSpacing(8)

        # Bubble container
        bubble = QWidget()
        bubble.setObjectName("userMessageBubble" if self.is_user else "assistantMessageBubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 10, 12, 10)
        bubble_layout.setSpacing(6)

        # Header for Assistant
        if not self.is_user:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(8)

            assistant_title = QLabel("R.I.A.T.A")
            assistant_title.setObjectName("assistantHeader")
            header_layout.addWidget(assistant_title)

            if intent_name:
                badge = QLabel(intent_name)
                badge.setObjectName("intentBadge")
                header_layout.addWidget(badge)

            header_layout.addStretch()

            time_lbl = QLabel(self.time_str)
            time_lbl.setObjectName("timestampLabel")
            header_layout.addWidget(time_lbl)

            bubble_layout.addLayout(header_layout)

        # Message Text
        msg_label = QLabel(text)
        msg_label.setObjectName("userMessageText" if self.is_user else "assistantMessageText")
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # Handle RTL vs LTR alignment
        if self.direction == "rtl":
            msg_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            msg_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            msg_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            msg_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        bubble_layout.addWidget(msg_label)

        # User timestamp footer
        if self.is_user:
            footer_layout = QHBoxLayout()
            footer_layout.addStretch()
            time_lbl = QLabel(self.time_str)
            time_lbl.setObjectName("timestampLabel")
            footer_layout.addWidget(time_lbl)
            bubble_layout.addLayout(footer_layout)

        # Alignment in timeline
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        bubble.setMaximumWidth(600)

        if self.is_user:
            outer_layout.addStretch()
            outer_layout.addWidget(bubble)
        else:
            outer_layout.addWidget(bubble)
            outer_layout.addStretch()
