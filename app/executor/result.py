"""
Execution result representation for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from dataclasses import dataclass, field
from typing import Any, Final, Optional

# Standard execution status codes
STATUS_SUCCESS: Final[str] = "SUCCESS"
STATUS_FAILED: Final[str] = "FAILED"
STATUS_INVALID_COMMAND: Final[str] = "INVALID_COMMAND"
STATUS_BACKEND_UNAVAILABLE: Final[str] = "BACKEND_UNAVAILABLE"
STATUS_PERMISSION_DENIED: Final[str] = "PERMISSION_DENIED"
STATUS_PATH_NOT_ALLOWED: Final[str] = "PATH_NOT_ALLOWED"
STATUS_APP_NOT_FOUND: Final[str] = "APP_NOT_FOUND"
STATUS_NOT_SUPPORTED: Final[str] = "NOT_SUPPORTED"
STATUS_TIMEOUT: Final[str] = "TIMEOUT"
STATUS_EXECUTION_ERROR: Final[str] = "EXECUTION_ERROR"


@dataclass
class ExecutionResult:
    """
    Language-agnostic execution result model.

    Guarantees honest reporting:
    - `success`: whether the intent was successfully fulfilled.
    - `executed`: whether a process or action was actually spawned on the OS.
    - `status`: machine-readable status code.
    - `message`: human-readable status message.
    - `data`: optional structured payload.
    """

    success: bool
    executed: bool = False
    status: str = STATUS_SUCCESS
    message: str = ""
    data: Optional[dict[str, Any]] = None
    intent_name: str = ""
    message_key: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    is_dry_run: bool = False
    action_summary: str = ""
    error: Optional[str] = None
    requires_context: bool = False
    context_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to serializable dictionary."""
        return {
            "success": self.success,
            "executed": self.executed,
            "status": self.status,
            "message": self.message or self.action_summary,
            "data": self.data,
            "intent_name": self.intent_name,
            "message_key": self.message_key,
            "params": self.params,
            "is_dry_run": self.is_dry_run,
            "action_summary": self.action_summary,
            "error": self.error,
            "requires_context": self.requires_context,
            "context_data": self.context_data,
        }
