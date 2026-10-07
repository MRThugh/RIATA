"""
Animated typing & thinking indicator for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Visually communicates when R.I.A.T.A is actively processing a command.
"""

from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)


class TypingIndicator(QWidget):
    """Subtle animated indicator showing R.I.A.T.A processing state."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("typingIndicatorWidget")
        self._dot_index = 0

        self._init_ui()
        self._init_timer()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self.label = QLabel("R.I.A.T.A")
        self.label.setObjectName("typingText")
        layout.addWidget(self.label)

        self.dots_label = QLabel("● ● ●")
        self.dots_label.setObjectName("typingDots")
        layout.addWidget(self.dots_label)

        self.setVisible(False)

    def _init_timer(self) -> None:
        self.timer = QTimer(self)
        self.timer.setInterval(320)
        self.timer.timeout.connect(self._animate_dots)

    def _animate_dots(self) -> None:
        patterns = ["● ○ ○", "○ ● ○", "○ ● ○", "● ● ●"]
        self._dot_index = (self._dot_index + 1) % len(patterns)
        self.dots_label.setText(patterns[self._dot_index])

    @property
    def is_active(self) -> bool:
        """Return True if typing animation is actively running."""
        return self.timer.isActive()

    def start(self, status_text: str = "R.I.A.T.A is working...") -> None:
        """Show indicator and start dot animation."""
        self.label.setText(status_text)
        self.setVisible(True)
        self.timer.start()

    def stop(self) -> None:
        """Hide indicator and halt animation."""
        self.timer.stop()
        self.setVisible(False)
