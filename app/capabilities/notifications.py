"""
Notifications capability foundation for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.engine.intent import Intent
from app.executor.result import STATUS_NOT_SUPPORTED, ExecutionResult


class NotificationsCapability(BaseCapability):
    """Architectural foundation for desktop notifications."""

    @property
    def id(self) -> str:
        return "notifications"

    @property
    def name(self) -> str:
        return "Desktop Notifications"

    @property
    def supported_intents(self) -> tuple[str, ...]:
        return ("SHOW_NOTIFICATION",)

    def execute(self, intent: Intent) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=intent.name,
            message="Notifications capability is under active development in v0.1.1.",
        )
