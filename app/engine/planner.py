"""
Command Planner and Multi-Step Engine for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)

Provides deterministic multi-step planning, step dependency mapping,
and execution status tracking without arbitrary code generation.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import get_config
from app.core.context.models import SessionContext
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.engine.matcher import BaseIntentParser, get_intent_parser
from app.executor.result import ExecutionResult

logger = get_logger("riata.planner")


@dataclass
class CommandStep:
    """Represents a single deterministic executable step within a CommandPlan."""

    step_id: int
    raw_text: str
    intent: Intent
    entities: dict[str, Any] = field(default_factory=dict)
    dependencies: list[int] = field(default_factory=list)
    risk_level: str = "low"
    status: str = "PENDING"  # PENDING, EXECUTING, SUCCESS, FAILED, SKIPPED, CANCELLED, BLOCKED
    result: Optional[ExecutionResult] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "raw_text": self.raw_text,
            "intent_name": self.intent.name,
            "confidence": round(self.intent.confidence, 3),
            "entities": self.entities,
            "dependencies": self.dependencies,
            "risk_level": self.risk_level,
            "status": self.status,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
        }


@dataclass
class CommandPlan:
    """Represents a structured execution plan containing one or more steps."""

    plan_id: str
    source_text: str
    steps: list[CommandStep] = field(default_factory=list)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: str = "PENDING"  # PENDING, IN_PROGRESS, SUCCESS, PARTIAL_SUCCESS, FAILED, BLOCKED, CANCELLED
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_single_step(self) -> bool:
        return len(self.steps) == 1

    @property
    def all_succeeded(self) -> bool:
        return bool(self.steps) and all(s.status == "SUCCESS" for s in self.steps)

    @property
    def has_failure(self) -> bool:
        return any(s.status == "FAILED" for s in self.steps)

    @property
    def has_partial_success(self) -> bool:
        success_count = sum(1 for s in self.steps if s.status == "SUCCESS")
        return success_count > 0 and (self.has_failure or any(s.status == "SKIPPED" for s in self.steps))

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "source_text": self.source_text,
            "step_count": len(self.steps),
            "status": self.status,
            "created_at": self.created_at,
            "steps": [s.to_dict() for s in self.steps],
            "context_snapshot": self.context_snapshot,
            "metadata": self.metadata,
        }


class CommandPlanner:
    """
    Parses complex natural commands into sequential, validated CommandSteps.
    """

    def __init__(self, parser: Optional[BaseIntentParser] = None) -> None:
        self.parser = parser or get_intent_parser()

    def build_plan(
        self,
        raw_text: str,
        context: Optional[SessionContext] = None,
    ) -> CommandPlan:
        """
        Construct a deterministic CommandPlan from raw user input.
        """
        cfg = get_config()
        clean = raw_text.strip()
        plan_id = f"plan-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"

        if not clean:
            unknown_intent = Intent.unknown(clean)
            step = CommandStep(
                step_id=1,
                raw_text="",
                intent=unknown_intent,
                entities={},
            )
            return CommandPlan(
                plan_id=plan_id,
                source_text="",
                steps=[step],
                status="FAILED",
            )

        # 1. Split multi-action clauses
        clauses = self._split_clauses(clean)
        if len(clauses) > cfg.max_plan_steps:
            logger.warning("Command clauses (%d) exceeded max allowed (%d)", len(clauses), cfg.max_plan_steps)
            clauses = clauses[: cfg.max_plan_steps]

        steps: list[CommandStep] = []
        ctx_snapshot = context.to_dict() if context else {}

        # 2. Build steps
        for i, clause in enumerate(clauses):
            step_id = i + 1
            # Parse clause
            parsed_intent = self.parser.parse(clause)
            deps = [i - 1] if i > 0 else []

            step = CommandStep(
                step_id=step_id,
                raw_text=clause,
                intent=parsed_intent,
                entities=dict(parsed_intent.entities),
                dependencies=deps,
                risk_level="high" if parsed_intent.name in ("DELETE_FILE", "SHUTDOWN", "RESTART") else "low",
                status="PENDING",
            )
            steps.append(step)

        plan = CommandPlan(
            plan_id=plan_id,
            source_text=clean,
            steps=steps,
            context_snapshot=ctx_snapshot,
            status="PENDING",
        )
        logger.info("Built CommandPlan '%s' with %d steps", plan_id, len(steps))
        return plan

    def _split_clauses(self, text: str) -> list[str]:
        """
        Split compound commands safely on linguistic coordinating conjunctions.
        Handles Persian ('و', 'و سپس', 'و بعد') and English ('and', 'and then', 'then').
        Avoids splitting words like 'Rock and Roll' or compound names.
        """
        cleaned = text.strip()

        # Persian multi-command connectors
        # e.g. "Chrome رو باز کن و GitHub رو باز کن"
        # e.g. "فولدر را باز کن و سپس فایل test.txt را بساز"
        fa_split_pattern = r"(?<=\S)\s+(?:و\s+سپس|و\s+بعد|سپس|و)\s+(?=\S)"

        # English multi-command connectors
        # e.g. "open Chrome and open GitHub"
        en_split_pattern = r"(?<=\S)\s+(?:and\s+then|then|and\s+after\s+that|and)\s+(?=\S)"

        # Check if text contains Persian characters
        is_persian = bool(re.search(r"[\u0600-\u06FF]", cleaned))
        pattern = fa_split_pattern if is_persian else en_split_pattern

        raw_parts = [p.strip() for p in re.split(pattern, cleaned, flags=re.IGNORECASE) if p.strip()]

        if len(raw_parts) <= 1:
            return [cleaned]

        # Verify that each part contains enough semantic substance to be an intent clause
        # (e.g. at least 2 words or a known command token)
        verified: list[str] = []
        for part in raw_parts:
            # If a part looks like an actual action command
            if len(part.split()) >= 1:
                verified.append(part)

        return verified if len(verified) >= 2 else [cleaned]


_GLOBAL_PLANNER: Optional[CommandPlanner] = None


def get_command_planner() -> CommandPlanner:
    """Retrieve global CommandPlanner instance."""
    global _GLOBAL_PLANNER
    if _GLOBAL_PLANNER is None:
        _GLOBAL_PLANNER = CommandPlanner()
    return _GLOBAL_PLANNER
