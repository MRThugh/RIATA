"""
Modern Sidebar for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Features session management, quick capabilities, theme/language toggles,
and responsive compact layout handling.
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_AUTHOR, APP_NAME, __version__
from app.ui.chat.conversation_item import ConversationItemWidget


class SidebarWidget(QWidget):
    """Modern collapsible sidebar inspired by Telegram Desktop / Discord navigation."""

    new_chat_requested = Signal()
    session_selected = Signal(str)
    theme_toggled = Signal()
    language_toggled = Signal()
    settings_requested = Signal()
    quick_tool_triggered = Signal(str)  # Emits tool command

    def __init__(self, dry_run: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.dry_run = dry_run
        self.setMinimumWidth(220)
        self.setMaximumWidth(280)

        self._session_items: dict[str, ConversationItemWidget] = {}
        self._active_session_id = "default"

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(12)

        # 1. Header (Logo + Version badge)
        header_widget = QWidget(self)
        header_widget.setObjectName("sidebarHeader")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        logo_label = QLabel(APP_NAME, header_widget)
        logo_label.setObjectName("sidebarLogo")
        title_row.addWidget(logo_label)

        version_badge = QLabel(f"v{__version__}", header_widget)
        version_badge.setObjectName("sidebarBadge")
        title_row.addWidget(version_badge)

        title_row.addStretch()
        header_layout.addLayout(title_row)

        sub_title = QLabel(f"Desktop Assistant • By {APP_AUTHOR}", header_widget)
        sub_title.setObjectName("convItemSubtitle")
        header_layout.addWidget(sub_title)

        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(6)

        dot = QLabel("●", header_widget)
        dot.setObjectName("statusDot")
        status_row.addWidget(dot)

        status_text = QLabel("ONLINE", header_widget)
        status_text.setObjectName("statusText")
        status_row.addWidget(status_text)

        if self.dry_run:
            dry_badge = QLabel("DRY RUN", header_widget)
            dry_badge.setObjectName("dryRunBadge")
            status_row.addWidget(dry_badge)

        status_row.addStretch()
        header_layout.addLayout(status_row)

        layout.addWidget(header_widget)

        # 2. New Chat Action
        self.new_chat_btn = QPushButton("+ New Chat / گفت‌وگوی جدید", self)
        self.new_chat_btn.setObjectName("newChatBtn")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        layout.addWidget(self.new_chat_btn)

        # 3. Sessions List (Scroll area)
        sessions_header = QLabel("CONVERSATIONS / گفت‌وگوها", self)
        sessions_header.setObjectName("convItemSubtitle")
        sessions_header.setStyleSheet("font-weight: 700; font-size: 10px; margin-top: 6px;")
        layout.addWidget(sessions_header)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.sessions_container = QWidget()
        self.sessions_layout = QVBoxLayout(self.sessions_container)
        self.sessions_layout.setContentsMargins(0, 0, 0, 0)
        self.sessions_layout.setSpacing(4)

        # Initial default conversation
        self.add_session("default", "Main Session", "Active workspace")

        self.sessions_layout.addStretch()
        self.scroll_area.setWidget(self.sessions_container)
        layout.addWidget(self.scroll_area, stretch=1)

        # 4. Quick Tools shortcuts
        tools_header = QLabel("QUICK TOOLS / ابزارها", self)
        tools_header.setObjectName("convItemSubtitle")
        tools_header.setStyleSheet("font-weight: 700; font-size: 10px; margin-top: 4px;")
        layout.addWidget(tools_header)

        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(6)

        sys_btn = QPushButton("⚙ Specs", self)
        sys_btn.setObjectName("chipButton")
        sys_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sys_btn.clicked.connect(lambda: self.quick_tool_triggered.emit("مشخصات سیستم"))
        tools_layout.addWidget(sys_btn)

        term_btn = QPushButton("⌨ Terminal", self)
        term_btn.setObjectName("chipButton")
        term_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        term_btn.clicked.connect(lambda: self.quick_tool_triggered.emit("ترمینال رو باز کن"))
        tools_layout.addWidget(term_btn)

        files_btn = QPushButton("📁 Files", self)
        files_btn.setObjectName("chipButton")
        files_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        files_btn.clicked.connect(lambda: self.quick_tool_triggered.emit("Downloads رو باز کن"))
        tools_layout.addWidget(files_btn)

        layout.addLayout(tools_layout)

        # 5. Bottom Actions (Language toggle, Theme toggle, Settings)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)

        self.lang_btn = QPushButton("🌐 FA / EN", self)
        self.lang_btn.setObjectName("actionIconButton")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.clicked.connect(self.language_toggled.emit)
        bottom_row.addWidget(self.lang_btn)

        self.theme_btn = QPushButton("🌓 Theme", self)
        self.theme_btn.setObjectName("actionIconButton")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        bottom_row.addWidget(self.theme_btn)

        self.settings_btn = QPushButton("⚙ Settings", self)
        self.settings_btn.setObjectName("actionIconButton")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        bottom_row.addWidget(self.settings_btn)

        layout.addLayout(bottom_row)

    def add_session(self, session_id: str, title: str, subtitle: str = "") -> None:
        """Add a conversation session to sidebar."""
        is_active = session_id == self._active_session_id
        item = ConversationItemWidget(session_id, title, subtitle, is_active=is_active, parent=self.sessions_container)
        item.clicked.connect(self._on_session_clicked)
        self._session_items[session_id] = item

        # Insert before stretch
        idx = max(0, self.sessions_layout.count() - 1)
        self.sessions_layout.insertWidget(idx, item)

    def set_active_session(self, session_id: str) -> None:
        """Set visual active state for session."""
        self._active_session_id = session_id
        for s_id, item in self._session_items.items():
            item.set_active(s_id == session_id)

    def _on_session_clicked(self, session_id: str) -> None:
        self.set_active_session(session_id)
        self.session_selected.emit(session_id)
