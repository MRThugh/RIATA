"""
Modern Input Composer for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Features auto-expanding height, Enter to submit, Shift+Enter for new line,
suggestion chips, and smooth focus indication.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CommandTextEdit(QTextEdit):
    """TextEdit that handles Enter to submit and Shift+Enter for newlines with auto-height."""

    submit_pressed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("messageInput")
        self.document().contentsChanged.connect(self._adjust_height)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Add newline on Shift+Enter
                super().keyPressEvent(event)
            else:
                # Submit command on plain Enter
                event.accept()
                self.submit_pressed.emit()
                return
        else:
            super().keyPressEvent(event)

    def _adjust_height(self) -> None:
        """Dynamically grow input height between 38px and 120px."""
        doc_height = int(self.document().size().height())
        target = max(38, min(120, doc_height + 12))
        self.setFixedHeight(target)


class MessageInputWidget(QWidget):
    """Bottom chat composer with suggestion chips and submit action."""

    message_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("inputAreaWidget")
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 12)
        main_layout.setSpacing(8)

        # 1. Quick suggestion chips bar
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(6)

        default_chips = [
            ("فایرفاکس رو باز کن", "فایرفاکس رو باز کن"),
            ("Open Firefox", "Open Firefox"),
            ("مشخصات سیستم", "مشخصات سیستم"),
            ("Downloads", "Downloads رو باز کن"),
            ("Another Love", "آهنگ Another Love رو پخش کن"),
        ]

        for label, cmd in default_chips:
            btn = QPushButton(label, self)
            btn.setObjectName("chipButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, text=cmd: self._send_chip(text))
            self.chips_layout.addWidget(btn)

        self.chips_layout.addStretch()
        main_layout.addLayout(self.chips_layout)

        # 2. Composer box container
        composer_container = QWidget(self)
        composer_container.setObjectName("inputBoxContainer")
        composer_layout = QHBoxLayout(composer_container)
        composer_layout.setContentsMargins(6, 4, 6, 4)
        composer_layout.setSpacing(8)

        self.text_edit = CommandTextEdit(composer_container)
        self.text_edit.setPlaceholderText(
            "پیام خود را بنویسید... (Enter برای ارسال) / Ask R.I.A.T.A anything..."
        )
        self.text_edit.submit_pressed.connect(self._on_submit)
        composer_layout.addWidget(self.text_edit, stretch=1)

        self.send_btn = QPushButton("ارسال / Send", composer_container)
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_submit)
        composer_layout.addWidget(self.send_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        main_layout.addWidget(composer_container)

    def _send_chip(self, text: str) -> None:
        """Directly trigger message submission from a quick chip."""
        self.message_submitted.emit(text)

    def _on_submit(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if text:
            self.message_submitted.emit(text)
            self.text_edit.clear()

    def set_enabled_state(self, enabled: bool) -> None:
        """Enable/disable input during async command execution."""
        self.text_edit.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        if enabled:
            self.text_edit.setFocus()

    def set_placeholder(self, text: str) -> None:
        """Update placeholder text based on active language."""
        self.text_edit.setPlaceholderText(text)
