"""
Applications capability for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.core.constants import (
    INTENT_CLOSE_APPLICATION,
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_URL,
)
from app.engine.intent import Intent
from app.executor.application import (
    execute_close_application,
    execute_open_application,
    execute_open_url,
)
from app.executor.result import (
    STATUS_INVALID_COMMAND,
    ExecutionResult,
)


class ApplicationsCapability(BaseCapability):
    """Handles application discovery, launching, closing, and web URL opening."""

    @property
    def id(self) -> str:
        return "applications"

    @property
    def name(self) -> str:
        return "Application Management"

    @property
    def supported_intents(self) -> tuple[str, ...]:
        return (INTENT_OPEN_APPLICATION, INTENT_CLOSE_APPLICATION, INTENT_OPEN_URL)

    def execute(self, intent: Intent) -> ExecutionResult:
        if intent.name == INTENT_OPEN_APPLICATION:
            return execute_open_application(intent)
        elif intent.name == INTENT_CLOSE_APPLICATION:
            return execute_close_application(intent)
        elif intent.name == INTENT_OPEN_URL:
            return execute_open_url(intent)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=intent.name,
            message="Unsupported application intent",
        )
