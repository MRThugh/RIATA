"""
Execution result representation for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExecutionResult:
    """
    Language-agnostic execution result.

    The executor does NOT contain Persian or English strings.
    It returns status, message keys, and parameters.
    The response generator formats it into the user's language.
    """

    success: bool
    intent_name: str
    message_key: str
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
            "intent_name": self.intent_name,
            "message_key": self.message_key,
            "params": self.params,
            "is_dry_run": self.is_dry_run,
            "action_summary": self.action_summary,
            "error": self.error,
            "requires_context": self.requires_context,
            "context_data": self.context_data,
        }
