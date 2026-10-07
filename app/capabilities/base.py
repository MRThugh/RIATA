"""
Base Capability abstraction for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)

Defines standardized contract and self-describing metadata for desktop capabilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.engine.intent import Intent
    from app.executor.result import ExecutionResult


class BaseCapability(ABC):
    """Abstract base class for all desktop interaction capabilities."""

    availability: str = "implemented"
    platform_support: tuple[str, ...] = ("linux",)

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique capability identifier (e.g. 'applications', 'filesystem')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable capability name."""
        pass

    @property
    @abstractmethod
    def supported_intents(self) -> tuple[str, ...]:
        """Tuple of intent names this capability can handle."""
        pass

    def can_handle(self, intent: Intent) -> bool:
        """Return True if this capability can process the given intent."""
        return intent.name in self.supported_intents

    def describe(self, intent: Intent) -> str:
        """Provide human-readable description of what this capability will do."""
        return f"{self.name}: {intent.name}"

    def validate(self, intent: Intent) -> tuple[bool, Optional[str]]:
        """
        Validate intent entities and prerequisites before execution.
        Returns (is_valid, error_message).
        """
        if not self.can_handle(intent):
            return False, f"Capability '{self.id}' does not support intent '{intent.name}'."
        return True, None

    @abstractmethod
    def execute(self, intent: Intent) -> ExecutionResult:
        """Safely execute the intent action and return an ExecutionResult."""
        pass

    def metadata(self) -> dict[str, Any]:
        """Return self-describing metadata for discovery and introspection."""
        return {
            "id": self.id,
            "name": self.name,
            "supported_intents": list(self.supported_intents),
            "description": (self.__doc__ or self.name).strip(),
            "availability": self.availability,
            "platform_support": list(self.platform_support),
        }
