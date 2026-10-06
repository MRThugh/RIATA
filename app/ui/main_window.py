"""
Main window desktop interface for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import get_config
from app.core.constants import (
    APP_AUTHOR,
    APP_FULL_NAME,
    APP_NAME,
    LANG_AUTO,
    LANG_ENGLISH,
    LANG_PERSIAN,
    __version__,
)
from app.core.logger import get_logger
from app.engine.router import IntentRouter, ProcessOutput, get_intent_router
from app.ui.chat_widget import ChatWidget
from app.ui.input_widget import InputWidget
from app.ui.styles import MAIN_STYLESHEET

logger = get_logger("riata.ui")


class ExecutionWorker(QObject):
    """Worker object executing intent processing off the UI thread."""

    finished = Signal(object)  # Emits ProcessOutput

    def __init__(self, router: IntentRouter, user_text: str) -> None:
        super().__init__()
        self.router = router
        self.user_text = user_text

    def run(self) -> None:
        output = self.router.process(self.user_text)
        self.finished.emit(output)


class MainWindow(QMainWindow):
    """Main desktop chat window for R.I.A.T.A."""

    def __init__(self) -> None:
        super().__init__()
        self.config = get_config()
        self.router = get_intent_router()
        self._current_thread: Optional[QThread] = None

        self._init_window()
        self._init_ui()
        self._show_welcome_message()

    def _init_window(self) -> None:
        self.setWindowTitle(f"{APP_NAME} v{__version__} — {APP_FULL_NAME}")
        self.resize(750, 700)
        self.setMinimumSize(500, 500)
        self.setStyleSheet(MAIN_STYLESHEET)

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar
        header = QWidget()
        header.setObjectName("headerWidget")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(12)

        # App Info Titles
        titles_layout = QVBoxLayout()
        titles_layout.setSpacing(2)
        app_title = QLabel(APP_NAME)
        app_title.setObjectName("appTitle")
        titles_layout.addWidget(app_title)

        app_sub = QLabel(f"{APP_FULL_NAME} • By {APP_AUTHOR}")
        app_sub.setObjectName("appSubtitle")
        titles_layout.addWidget(app_sub)
        header_layout.addLayout(titles_layout)

        header_layout.addStretch()

        # Dry Run Indicator
        if self.config.dry_run:
            dry_badge = QLabel("DRY RUN")
            dry_badge.setObjectName("dryRunBadge")
            header_layout.addWidget(dry_badge)

        # Online Status
        status_box = QHBoxLayout()
        status_box.setSpacing(4)
        dot = QLabel("●")
        dot.setObjectName("statusDot")
        status_box.addWidget(dot)
        status_lbl = QLabel("ONLINE")
        status_lbl.setObjectName("statusText")
        status_box.addWidget(status_lbl)
        header_layout.addLayout(status_box)

        # Clear Chat Button
        clear_btn = QPushButton("پاک کردن / Clear")
        clear_btn.setObjectName("headerBtn")
        clear_btn.clicked.connect(self._clear_chat)
        header_layout.addWidget(clear_btn)

        main_layout.addWidget(header)

        # 2. Chat Timeline
        self.chat_widget = ChatWidget(self)
        main_layout.addWidget(self.chat_widget)

        # 3. Input Bar
        self.input_widget = InputWidget(self)
        self.input_widget.message_submitted.connect(self._handle_user_message)
        main_layout.addWidget(self.input_widget)

    def _show_welcome_message(self) -> None:
        """Display initial friendly greeting with instructions."""
        welcome_text = (
            "سلام! به R.I.A.T.A خوش آمدید.\n"
            "من دستیار هوشمند و محلی دستورات اوبونتو هستم.\n\n"
            "می‌توانید به زبان فارسی یا انگلیسی درخواست دهید:\n"
            "• «فایرفاکس رو باز کن» یا \"Open Firefox\"\n"
            "• «پوشه Downloads رو باز کن»\n"
            "• «آهنگ Another Love رو پخش کن»\n"
            "• «مشخصات سیستم» یا \"System info\"\n\n"
            "چه کاری برات انجام بدم؟"
        )
        self.chat_widget.add_message(
            text=welcome_text,
            is_user=False,
            intent_name="ONLINE",
            direction="rtl",
        )

    def _handle_user_message(self, text: str) -> None:
        """Process incoming user message asynchronously."""
        # Detect direction for user message bubble
        is_persian = any("\u0600" <= c <= "\u06FF" for c in text)
        user_dir = "rtl" if is_persian else "ltr"

        # Add user bubble immediately
        self.chat_widget.add_message(text=text, is_user=True, direction=user_dir)
        self.input_widget.set_enabled_state(False)

        # Run intent processing and execution in background thread
        self._thread = QThread()
        self._worker = ExecutionWorker(self.router, text)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_execution_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_execution_finished(self, output: ProcessOutput) -> None:
        """Handle output from execution worker."""
        self.input_widget.set_enabled_state(True)

        intent_name = output.intent.name if output.intent else None
        self.chat_widget.add_message(
            text=output.response_text,
            is_user=False,
            intent_name=intent_name,
            direction=output.direction,
        )

        # If user commanded application exit
        if output.is_exit:
            QTimer.singleShot(1500, self.close)

    def _clear_chat(self) -> None:
        """Clear conversation and reset context."""
        self.chat_widget.clear_messages()
        self.router.reset_context()
        self._show_welcome_message()
