"""
Task Composition Foundation for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Data model and execution structures for single and composite tasks.
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid

from app.engine.intent import Intent
from app.executor.result import ExecutionResult


@dataclass
class TaskStep:
    """A single discrete step inside a compound task."""

    intent: Intent
    result: Optional[ExecutionResult] = None
    executed: bool = False


@dataclass
class Task:
    """
    Representation of a user task composed of one or more intent steps.
    Foundation for future multi-step automation.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str = ""
    steps: list[TaskStep] = field(default_factory=list)
    status: str = "PENDING"  # PENDING, IN_PROGRESS, SUCCESS, FAILED
    language: str = "en"

    @property
    def is_composite(self) -> bool:
        """Return True if this task contains multiple intent actions."""
        return len(self.steps) > 1

    def add_intent(self, intent: Intent) -> None:
        """Append an intent step to this task."""
        self.steps.append(TaskStep(intent=intent))
