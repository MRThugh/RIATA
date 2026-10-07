"""
Modern Main Desktop Window for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Inspired by the interaction quality and layout philosophy of applications
like Telegram Desktop and Discord. Built entirely with native PySide6 / Qt 6.
"""

from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.core.config import get_config
from app.core.constants import (
    APP_FULL_NAME,
    APP_NAME,
    __version__,
)
from app.core.logger import get_logger
from app.engine.router import IntentRouter, ProcessOutput, get_intent_router
from app.ui.chat.chat_view import ChatView
from app.ui.dialogs.settings_dialog import SettingsDialog
from app.ui.input.message_input import MessageInputWidget
from app.ui.shell.header import HeaderBarWidget
from app.ui.shell.sidebar import SidebarWidget
from app.ui.themes.manager import get_theme_manager

logger = get_logger("riata.ui.main")


class ExecutionWorker(QObject):
    """Worker object executing intent processing asynchronously off the UI thread."""

    finished = Signal(object)  # Emits ProcessOutput

    def __init__(self, router: IntentRouter, user_text: str) -> None:
        super().__init__()
        self.router = router
        self.user_text = user_text

    def run(self) -> None:
        try:
            output = self.router.process(self.user_text)
            self.finished.emit(output)
        except Exception as e:
            logger.exception("Error in execution worker: %s", e)


class MainWindow(QMainWindow):
    """
    Modern conversational desktop assistant application for R.I.A.T.A.
    Features collapsible responsive sidebar, conversation history,
    smooth animations, dynamic RTL/LTR language toggling, and live theming.
    """

    def __init__(self) -> None:
        super().__init__()
        self.config = get_config()
        self.router = get_intent_router()
        self.theme_manager = get_theme_manager()

        self._current_thread: Optional[QThread] = None
        self._current_language: str = "fa"  # Persian default
        self._session_histories: dict[str, list[dict]] = {"default": []}
        self._active_session_id = "default"
        self._session_counter = 1

        self._init_window()
        self._init_ui()
        self._show_welcome_message()

    def _init_window(self) -> None:
        self.setWindowTitle(f"{APP_NAME} v{__version__} — {APP_FULL_NAME}")
        self.resize(880, 720)
        self.setMinimumSize(480, 480)

        # Set initial layout direction (RTL for Persian)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._apply_theme()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Main horizontal shell layout: [Sidebar | Chat Column]
        self.main_shell_layout = QHBoxLayout(central_widget)
        self.main_shell_layout.setContentsMargins(0, 0, 0, 0)
        self.main_shell_layout.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = SidebarWidget(dry_run=self.config.dry_run, parent=central_widget)
        self.sidebar.new_chat_requested.connect(self._create_new_chat)
        self.sidebar.session_selected.connect(self._switch_session)
        self.sidebar.theme_toggled.connect(self._toggle_theme)
        self.sidebar.language_toggled.connect(self._toggle_language)
        self.sidebar.settings_requested.connect(self._open_settings)
        self.sidebar.quick_tool_triggered.connect(self._handle_user_message)
        self.main_shell_layout.addWidget(self.sidebar)

        # 2. Right Chat Container
        chat_container = QWidget(central_widget)
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Header Bar
        self.header = HeaderBarWidget(parent=chat_container)
        self.header.toggle_sidebar_requested.connect(self._toggle_sidebar)
        self.header.clear_chat_requested.connect(self._clear_chat)
        self.header.theme_toggled.connect(self._toggle_theme)
        self.header.language_toggled.connect(self._toggle_language)
        chat_layout.addWidget(self.header)

        # Chat View
        self.chat_view = ChatView(parent=chat_container)
        chat_layout.addWidget(self.chat_view, stretch=1)

        # Message Input Composer
        self.input_widget = MessageInputWidget(parent=chat_container)
        self.input_widget.message_submitted.connect(self._handle_user_message)
        chat_layout.addWidget(self.input_widget)

        self.main_shell_layout.addWidget(chat_container, stretch=1)

    def _apply_theme(self) -> None:
        """Apply active theme stylesheet to the entire window hierarchy."""
        self.setStyleSheet(self.theme_manager.generate_stylesheet())

    def _toggle_theme(self) -> None:
        """Toggle between Dark and Light mode live."""
        self.theme_manager.toggle_theme()
        self._apply_theme()

    def _toggle_language(self) -> None:
        """Dynamically toggle between Persian (RTL) and English (LTR)."""
        if self._current_language == "fa":
            self._current_language = "en"
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            self.header.set_conversation_title("R.I.A.T.A Conversation", "Deterministic Desktop Assistant")
            self.input_widget.set_placeholder("Type a command... (Press Enter to send)")
        else:
            self._current_language = "fa"
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.header.set_conversation_title("گفت‌وگوی ریاتا", "دستیار هوشمند و قطعی اوبونتو")
            self.input_widget.set_placeholder("پیام خود را بنویسید... (Enter برای ارسال)")

    def _toggle_sidebar(self) -> None:
        """Toggle sidebar visibility on user request."""
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Responsive layout behavior on window resize."""
        super().resizeEvent(event)
        # On very narrow windows, collapse sidebar into drawer
        if self.width() < 640 and self.sidebar.isVisible():
            self.sidebar.setVisible(False)
        elif self.width() >= 720 and not self.sidebar.isVisible():
            self.sidebar.setVisible(True)

    def _show_welcome_message(self) -> None:
        """Display initial friendly assistant welcome card."""
        if self._current_language == "fa":
            welcome_text = (
                "سلام! به R.I.A.T.A خوش آمدید.\n"
                "من دستیار هوشمند، محلی و بدون هوش مصنوعی ابری اوبونتو هستم.\n\n"
                "می‌توانید به زبان فارسی یا انگلیسی فرمان دهید:\n"
                "• «فایرفاکس رو باز کن» یا \"Open Firefox\"\n"
                "• «پوشه Downloads رو باز کن»\n"
                "• «آهنگ Another Love رو پخش کن»\n"
                "• «مشخصات سیستم» یا \"System info\"\n\n"
                "چه کاری برات انجام بدم؟"
            )
            msg_dir = "rtl"
        else:
            welcome_text = (
                "Hello! Welcome to R.I.A.T.A.\n"
                "I am your local, deterministic Ubuntu desktop assistant.\n\n"
                "You can command in Persian or English:\n"
                "• \"Open Firefox\"\n"
                "• \"Open Downloads\"\n"
                "• \"Play Another Love\"\n"
                "• \"System info\"\n\n"
                "How can I help you today?"
            )
            msg_dir = "ltr"

        self.chat_view.add_message(
            text=welcome_text,
            is_user=False,
            intent_name="ONLINE",
            direction=msg_dir,
            animate=True,
        )

    def _handle_user_message(self, text: str) -> None:
        """Process incoming user command asynchronously."""
        cleaned = text.strip()
        if not cleaned:
            return

        is_persian = any("\u0600" <= c <= "\u06FF" for c in cleaned)
        user_dir = "rtl" if is_persian else "ltr"

        # 1. Add user bubble
        self.chat_view.add_message(text=cleaned, is_user=True, direction=user_dir, animate=True)
        self._record_message(self._active_session_id, cleaned, is_user=True, direction=user_dir)

        # 2. Show thinking/typing indicator & disable input
        thinking_text = "در حال پردازش..." if is_persian else "R.I.A.T.A is working..."
        self.chat_view.set_typing(True, thinking_text)
        self.input_widget.set_enabled_state(False)

        # 3. Offload processing to background QThread
        self._thread = QThread()
        self._worker = ExecutionWorker(self.router, cleaned)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_execution_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_execution_finished(self, output: ProcessOutput) -> None:
        """Handle execution completion on the UI thread."""
        self.chat_view.set_typing(False)
        self.input_widget.set_enabled_state(True)

        intent_name = output.intent.name if output.intent else None
        self.chat_view.add_message(
            text=output.response_text,
            is_user=False,
            intent_name=intent_name,
            direction=output.direction,
            animate=True,
        )
        self._record_message(
            self._active_session_id,
            output.response_text,
            is_user=False,
            intent_name=intent_name,
            direction=output.direction,
        )

        if output.is_exit:
            QTimer.singleShot(1500, self.close)

    def _record_message(
        self,
        session_id: str,
        text: str,
        is_user: bool,
        intent_name: Optional[str] = None,
        direction: str = "ltr",
    ) -> None:
        if session_id not in self._session_histories:
            self._session_histories[session_id] = []
        self._session_histories[session_id].append({
            "text": text,
            "is_user": is_user,
            "intent_name": intent_name,
            "direction": direction,
        })

    def _create_new_chat(self) -> None:
        """Start a fresh conversation thread."""
        self._session_counter += 1
        new_id = f"session_{self._session_counter}"
        title = f"Chat {self._session_counter}"
        subtitle = "New conversation"

        self._session_histories[new_id] = []
        self.sidebar.add_session(new_id, title, subtitle)
        self._switch_session(new_id)

    def _switch_session(self, session_id: str) -> None:
        """Switch to another conversation session."""
        self._active_session_id = session_id
        self.sidebar.set_active_session(session_id)
        self.chat_view.clear_messages()
        self.router.reset_context()

        # Restore message history or show welcome message
        history = self._session_histories.get(session_id, [])
        if not history:
            self._show_welcome_message()
        else:
            for msg in history:
                self.chat_view.add_message(
                    text=msg["text"],
                    is_user=msg["is_user"],
                    intent_name=msg.get("intent_name"),
                    direction=msg.get("direction", "ltr"),
                    animate=False,
                )

    def _clear_chat(self) -> None:
        """Clear active conversation."""
        self.chat_view.clear_messages()
        self._session_histories[self._active_session_id] = []
        self.router.reset_context()
        self._show_welcome_message()

    def _open_settings(self) -> None:
        """Open settings dialog."""
        dialog = SettingsDialog(self)
        dialog.exec()
