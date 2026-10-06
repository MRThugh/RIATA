"""
Chat input widget with keyboard shortcuts for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QWidget,
)


class CommandInputEdit(QTextEdit):
    """TextEdit that handles Enter to send and Shift+Enter for new line."""

    submit_pressed = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Insert newline on Shift+Enter
                super().keyPressEvent(event)
            else:
                # Submit on plain Enter
                event.accept()
                self.submit_pressed.emit()
                return
        else:
            super().keyPressEvent(event)


class InputWidget(QWidget):
    """Bottom input bar with text area and send action button."""

    message_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("inputAreaWidget")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(10)

        # Multiline text input with limited height
        self.text_edit = CommandInputEdit()
        self.text_edit.setObjectName("messageInput")
        self.text_edit.setPlaceholderText("پیام خود را بنویسید... (Enter برای ارسال) / Type a command...")
        self.text_edit.setFixedHeight(44)
        self.text_edit.submit_pressed.connect(self._on_submit)
        layout.addWidget(self.text_edit)

        # Send button
        self.send_btn = QPushButton("ارسال / Send")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setFixedHeight(44)
        self.send_btn.clicked.connect(self._on_submit)
        layout.addWidget(self.send_btn)

    def _on_submit(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if text:
            self.message_submitted.emit(text)
            self.text_edit.clear()

    def set_enabled_state(self, enabled: bool) -> None:
        """Enable or disable input during execution."""
        self.text_edit.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        if enabled:
            self.text_edit.setFocus()
