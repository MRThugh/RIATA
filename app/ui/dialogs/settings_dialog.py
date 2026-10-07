"""
Settings & About dialog for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import get_config
from app.core.constants import APP_AUTHOR, APP_FULL_NAME, APP_GITHUB, APP_NAME, __version__


class SettingsDialog(QDialog):
    """Clean settings & info dialog for R.I.A.T.A."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config = get_config()
        self.setWindowTitle(f"{APP_NAME} — Settings & About")
        self.setFixedSize(460, 420)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header info
        title_row = QHBoxLayout()
        title_label = QLabel(APP_NAME, self)
        title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #38bdf8;")
        title_row.addWidget(title_label)

        version_label = QLabel(f"v{__version__}", self)
        version_label.setStyleSheet("background: #1e293b; color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-family: monospace;")
        title_row.addWidget(version_label)
        title_row.addStretch()
        layout.addLayout(title_row)

        desc = QLabel(
            f"{APP_FULL_NAME}\n"
            f"Author: {APP_AUTHOR}\n"
            f"GitHub: {APP_GITHUB}",
            self,
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc)

        divider = QLabel("", self)
        divider.setStyleSheet("border-bottom: 1px solid #334155;")
        layout.addWidget(divider)

        # Settings
        settings_title = QLabel("Execution Settings / تنظیمات اجرا", self)
        settings_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #f8fafc;")
        layout.addWidget(settings_title)

        self.dry_run_check = QCheckBox("Dry-run mode (حالت شبیه‌سازی بدون اجرای سیستم)", self)
        self.dry_run_check.setChecked(self.config.dry_run)
        self.dry_run_check.toggled.connect(self._on_dry_run_toggled)
        layout.addWidget(self.dry_run_check)

        self.safe_check = QCheckBox("Safe Execution allowlist policy (حالت ایمن)", self)
        self.safe_check.setChecked(self.config.safe_execution)
        self.safe_check.toggled.connect(self._on_safe_toggled)
        layout.addWidget(self.safe_check)

        arch_info = QLabel(
            "Architecture v0.2.0:\n"
            "• Context-Aware Multi-Turn Interaction Platform\n"
            "• Pronoun & Deictic Contextual Entity Resolution\n"
            "• Deterministic Multi-Step Command Planner\n"
            "• Single-Use Non-Replayable Security Tokens\n"
            "• Risk-Aware Policy Engine (ALLOW, CONFIRM, DENY)\n"
            "• Modular Desktop Capabilities & Filesystem Sandbox",
            self,
        )
        arch_info.setStyleSheet("color: #64748b; font-size: 11px; line-height: 1.4;")
        layout.addWidget(arch_info)

        layout.addStretch()

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close / بستن", self)
        close_btn.setObjectName("actionIconButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _on_dry_run_toggled(self, checked: bool) -> None:
        self.config.dry_run = checked

    def _on_safe_toggled(self, checked: bool) -> None:
        self.config.safe_execution = checked
