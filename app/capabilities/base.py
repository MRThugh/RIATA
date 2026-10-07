"""
Base Capability abstraction for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Defines the contract for modular desktop capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.engine.intent import Intent
from app.executor.result import ExecutionResult


class BaseCapability(ABC):
    """Abstract base class for all desktop interaction capabilities."""

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

    @abstractmethod
    def execute(self, intent: Intent) -> ExecutionResult:
        """Safely execute the intent action and return an ExecutionResult."""
        pass
