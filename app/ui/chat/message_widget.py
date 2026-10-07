"""
Modern Message Widget for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Inspired by modern conversational desktop clients (Telegram Desktop / Discord).
Supports subtle entry fade animation, word-wrap, selectable text, and RTL/LTR dynamics.
"""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MessageWidget(QWidget):
    """Visual chat bubble widget for both user commands and assistant responses."""

    def __init__(
        self,
        text: str,
        is_user: bool = False,
        intent_name: Optional[str] = None,
        direction: str = "ltr",
        timestamp: Optional[str] = None,
        animate: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.is_user = is_user
        self.direction = direction
        self.time_str = timestamp or datetime.now().strftime("%H:%M")

        self._init_ui(text, intent_name)
        if animate:
            self._start_fade_animation()

    def _init_ui(self, text: str, intent_name: Optional[str]) -> None:
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(18, 5, 18, 5)
        outer_layout.setSpacing(10)

        # Bubble card
        bubble = QWidget(self)
        bubble.setObjectName("userMessageBubble" if self.is_user else "assistantMessageBubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 10)
        bubble_layout.setSpacing(6)

        # Header for Assistant
        if not self.is_user:
            header_layout = QHBoxLayout()
            header_layout.setSpacing(8)

            assistant_title = QLabel("R.I.A.T.A", bubble)
            assistant_title.setObjectName("assistantHeader")
            header_layout.addWidget(assistant_title)

            if intent_name:
                badge = QLabel(intent_name, bubble)
                badge.setObjectName("intentBadge")
                header_layout.addWidget(badge)

            header_layout.addStretch()

            time_lbl = QLabel(self.time_str, bubble)
            time_lbl.setObjectName("timestampLabel")
            header_layout.addWidget(time_lbl)

            bubble_layout.addLayout(header_layout)

        # Message Text
        msg_label = QLabel(text, bubble)
        msg_label.setObjectName("userMessageText" if self.is_user else "assistantMessageText")
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # RTL vs LTR alignment
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
            time_lbl = QLabel(self.time_str, bubble)
            time_lbl.setObjectName("timestampLabel")
            footer_layout.addWidget(time_lbl)
            bubble_layout.addLayout(footer_layout)

        # Bubble sizing and layout alignment
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        bubble.setMaximumWidth(620)

        if self.is_user:
            outer_layout.addStretch()
            outer_layout.addWidget(bubble)
        else:
            outer_layout.addWidget(bubble)
            outer_layout.addStretch()

    def _start_fade_animation(self) -> None:
        """Subtle non-blocking opacity fade-in animation."""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(160)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
