"""
Clipboard capability foundation for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.engine.intent import Intent
from app.executor.result import STATUS_NOT_SUPPORTED, ExecutionResult


class ClipboardCapability(BaseCapability):
    """Architectural foundation for desktop clipboard integration."""

    availability: str = "foundation"
    platform_support: tuple[str, ...] = ("linux",)

    @property
    def id(self) -> str:
        return "clipboard"

    @property
    def name(self) -> str:
        return "Clipboard"

    @property
    def supported_intents(self) -> tuple[str, ...]:
        return ("COPY_TO_CLIPBOARD", "PASTE_FROM_CLIPBOARD")

    def execute(self, intent: Intent) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=intent.name,
            message="Clipboard management is an architectural foundation planned for future releases. Platform clipboard access is currently not supported.",
        )
