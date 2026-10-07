"""
System capability for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.core.constants import (
    INTENT_EXIT_APPLICATION,
    INTENT_OPEN_FILE_MANAGER,
    INTENT_OPEN_SETTINGS,
    INTENT_OPEN_TERMINAL,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_TAKE_SCREENSHOT,
)
from app.engine.intent import Intent
from app.executor.result import STATUS_INVALID_COMMAND, ExecutionResult
from app.executor.system import (
    execute_exit_application,
    execute_open_file_manager,
    execute_open_settings,
    execute_open_terminal,
    execute_show_system_info,
    execute_take_screenshot,
)


class SystemCapability(BaseCapability):
    """Handles system introspection, utilities, terminal, settings, and screenshots."""

    @property
    def id(self) -> str:
        return "system"

    @property
    def name(self) -> str:
        return "System Utilities"

    @property
    def supported_intents(self) -> tuple[str, ...]:
        return (
            INTENT_SHOW_SYSTEM_INFO,
            INTENT_OPEN_TERMINAL,
            INTENT_OPEN_FILE_MANAGER,
            INTENT_OPEN_SETTINGS,
            INTENT_TAKE_SCREENSHOT,
            INTENT_EXIT_APPLICATION,
        )

    def execute(self, intent: Intent) -> ExecutionResult:
        handlers = {
            INTENT_SHOW_SYSTEM_INFO: execute_show_system_info,
            INTENT_OPEN_TERMINAL: execute_open_terminal,
            INTENT_OPEN_FILE_MANAGER: execute_open_file_manager,
            INTENT_OPEN_SETTINGS: execute_open_settings,
            INTENT_TAKE_SCREENSHOT: execute_take_screenshot,
            INTENT_EXIT_APPLICATION: execute_exit_application,
        }
        handler = handlers.get(intent.name)
        if handler:
            return handler(intent)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=intent.name,
            message="Unsupported system utility",
        )
