"""
Filesystem capability for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from app.capabilities.base import BaseCapability
from app.core.constants import INTENT_OPEN_FILE, INTENT_OPEN_FOLDER
from app.engine.intent import Intent
from app.executor.files import execute_open_file, execute_open_folder
from app.executor.result import (
    STATUS_INVALID_COMMAND,
    ExecutionResult,
)


class FilesystemCapability(BaseCapability):
    """Handles sandboxed filesystem operations for folders and files."""

    @property
    def id(self) -> str:
        return "filesystem"

    @property
    def name(self) -> str:
        return "Filesystem & Folders"

    @property
    def supported_intents(self) -> tuple[str, ...]:
        return (INTENT_OPEN_FOLDER, INTENT_OPEN_FILE)

    def execute(self, intent: Intent) -> ExecutionResult:
        if intent.name == INTENT_OPEN_FOLDER:
            return execute_open_folder(intent)
        elif intent.name == INTENT_OPEN_FILE:
            return execute_open_file(intent)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=intent.name,
            message="Unsupported filesystem action",
        )
