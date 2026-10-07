"""
Applications capability for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.core.constants import INTENT_OPEN_APPLICATION
from app.engine.intent import Intent
from app.executor.application import execute_open_application
from app.executor.result import ExecutionResult


class ApplicationsCapability(BaseCapability):
    """Handles application discovery, launching, and lifecycle management."""

    @property
    def id(self) -> str:
        return "applications"

    @property
    def name(self) -> str:
        return "Application Management"

    @property
    def supported_intents(self) -> tuple[str, ...]:
        return (INTENT_OPEN_APPLICATION,)

    def execute(self, intent: Intent) -> ExecutionResult:
        return execute_open_application(intent)
