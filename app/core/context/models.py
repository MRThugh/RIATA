"""
Session and Interaction Context Models for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)

Provides structured, typed, deterministic context models for tracking
conversational state across turns (active app, active directory, active file,
open applications, pending confirmation, and conversation history).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.engine.intent import Intent
    from app.executor.result import ExecutionResult


@dataclass
class PendingConfirmation:
    """
    Cryptographically and session-bound pending confirmation token.

    Security Properties:
    - Bound to a specific session_id
    - Bound to a specific intent, action name, and entity fingerprint
    - Has an explicit expiration timestamp
    - Cannot be replayed once consumed or rejected
    """

    confirmation_id: str
    session_id: str
    action: str
    intent: Intent
    entities: dict[str, Any] = field(default_factory=dict)
    action_label: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    status: str = "PENDING"  # PENDING, CONFIRMED, REJECTED, EXPIRED, CONSUMED
    plan_id: Optional[str] = None

    def is_valid(self, current_time: Optional[float] = None) -> bool:
        """Verify confirmation is still in PENDING status and not expired."""
        now = current_time if current_time is not None else time.time()
        if self.status != "PENDING":
            return False
        if self.expires_at > 0.0 and now > self.expires_at:
            self.status = "EXPIRED"
            return False
        return True

    def matches(self, session_id: str, intent_name: str, entities: Optional[dict[str, Any]] = None) -> bool:
        """Verify that an action and entity fingerprint match this pending token."""
        if self.session_id != session_id:
            return False
        if self.action != intent_name:
            return False
        if entities is not None and self.entities != entities:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "confirmation_id": self.confirmation_id,
            "session_id": self.session_id,
            "action": self.action,
            "action_label": self.action_label,
            "entities": dict(self.entities),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "intent_name": self.intent.name if self.intent else "",
            "intent": self.intent.to_dict() if self.intent else None,
            "plan_id": self.plan_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Optional[PendingConfirmation]:
        if not data:
            return None
        from app.engine.intent import Intent

        if data.get("intent") and isinstance(data["intent"], dict):
            intent = Intent.from_dict(data["intent"])
        else:
            intent = Intent(
                name=data.get("action") or data.get("intent_name", ""),
                confidence=1.0,
                entities=dict(data.get("entities", {})),
            )
        return cls(
            confirmation_id=data.get("confirmation_id", ""),
            session_id=data.get("session_id", ""),
            action=data.get("action", ""),
            action_label=data.get("action_label", ""),
            intent=intent,
            entities=dict(data.get("entities", {})),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at", 0.0),
            status=data.get("status", "PENDING"),
            plan_id=data.get("plan_id"),
        )


@dataclass
class SessionContext:
    """
    Bounded, typed session context representing a user interaction stream.

    Tracks active contextual entities (application, directory, file)
    and conversation turns without unbounded memory growth.
    """

    session_id: str = "default"
    current_intent: Optional[Intent] = None
    previous_intent: Optional[Intent] = None
    active_entities: dict[str, Any] = field(default_factory=dict)
    active_application: Optional[str] = None
    active_file: Optional[str] = None
    active_directory: Optional[str] = None
    open_applications: list[str] = field(default_factory=list)
    pending_confirmation: Optional[PendingConfirmation] = None
    pending_plan: Optional[Any] = None
    pending_step_index: int = 0
    last_result: Optional[ExecutionResult] = None
    last_error: Optional[str] = None
    conversation_turn: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    history: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_turn(
        self,
        intent: Intent,
        result: ExecutionResult,
        entities: Optional[dict[str, Any]] = None,
        max_history: int = 20,
    ) -> None:
        """
        Record a completed turn and update active entities predictably.
        Crucial security invariant: Context is only updated with facts actually
        established by successful execution (result.success == True).
        """
        now = time.time()
        self.updated_at = now
        self.conversation_turn += 1
        self.previous_intent = self.current_intent
        self.current_intent = intent
        self.last_result = result

        if not result.success and result.error:
            self.last_error = result.error
        else:
            self.last_error = None

        ents = dict(entities or intent.entities or {})

        # Context update rules based ONLY on successfully executed intent
        if result.success:
            self.active_entities.update(ents)

            # Applications
            if intent.name == "OPEN_APPLICATION":
                app_val = ents.get("application")
                if app_val:
                    self.active_application = str(app_val)
                    if str(app_val).lower() not in [a.lower() for a in self.open_applications]:
                        self.open_applications.append(str(app_val))
            elif intent.name == "CLOSE_APPLICATION":
                app_val = ents.get("application") or self.active_application
                if app_val:
                    self.open_applications = [
                        a for a in self.open_applications if a.lower() != str(app_val).lower()
                    ]
                    # If the active application was closed, clear it to avoid stale state.
                    # Do not arbitrarily select a replacement application.
                    if self.active_application and self.active_application.lower() == str(app_val).lower():
                        self.active_application = None

            # Folders & Files
            if intent.name in ("OPEN_FOLDER", "CREATE_FOLDER"):
                folder_val = ents.get("folder")
                if folder_val:
                    self.active_directory = str(folder_val)
            elif intent.name in ("OPEN_FILE", "CREATE_FILE"):
                file_val = ents.get("file")
                if file_val:
                    self.active_file = str(file_val)
            elif intent.name == "DELETE_FILE":
                file_val = ents.get("file")
                if file_val and self.active_file and self.active_file.lower() == str(file_val).lower():
                    self.active_file = None

        # Bounded history ring buffer
        turn_record = {
            "turn": self.conversation_turn,
            "timestamp": now,
            "intent": intent.name,
            "success": result.success,
            "executed": result.executed,
            "status": result.status,
            "entities": ents,
            "raw_text": intent.raw_text,
        }
        self.history.append(turn_record)
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]

    def clear(self) -> None:
        """Reset contextual entities, pending confirmations, and pending plans."""
        self.current_intent = None
        self.previous_intent = None
        self.active_entities.clear()
        self.active_application = None
        self.active_file = None
        self.active_directory = None
        self.open_applications.clear()
        self.pending_confirmation = None
        self.pending_plan = None
        self.pending_step_index = 0
        self.last_result = None
        self.last_error = None
        self.updated_at = time.time()
        self.history.clear()
        self.metadata.clear()

    def to_dict(self, include_pending_confirmation: bool = True) -> dict[str, Any]:
        """Convert session context to complete serializable dictionary."""
        has_pending = self.pending_confirmation is not None and self.pending_confirmation.is_valid()
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "conversation_turn": self.conversation_turn,
            "active_application": self.active_application,
            "active_directory": self.active_directory,
            "active_file": self.active_file,
            "open_applications": list(self.open_applications),
            "previous_intent": self.previous_intent.to_dict() if self.previous_intent else None,
            "current_intent": self.current_intent.to_dict() if self.current_intent else None,
            "has_pending_confirmation": has_pending if include_pending_confirmation else False,
            "pending_confirmation": self.pending_confirmation.to_dict() if (include_pending_confirmation and self.pending_confirmation) else None,
            "active_entities": dict(self.active_entities),
            "history": [dict(h) for h in self.history],
            "history_count": len(self.history),
            "last_result": self.last_result.to_dict() if self.last_result else None,
            "last_error": self.last_error,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], restore_confirmation: bool = False) -> SessionContext:
        """
        Reconstruct SessionContext from dictionary.
        By default, pending confirmations and plans are invalidated across disk restoration.
        """
        from app.engine.intent import Intent
        from app.executor.result import ExecutionResult

        prev_intent = None
        if data.get("previous_intent"):
            if isinstance(data["previous_intent"], dict):
                prev_intent = Intent.from_dict(data["previous_intent"])
            elif isinstance(data["previous_intent"], str):
                prev_intent = Intent(name=data["previous_intent"], confidence=1.0)

        curr_intent = None
        if data.get("current_intent"):
            if isinstance(data["current_intent"], dict):
                curr_intent = Intent.from_dict(data["current_intent"])
            elif isinstance(data["current_intent"], str):
                curr_intent = Intent(name=data["current_intent"], confidence=1.0)

        last_res = None
        if data.get("last_result") and isinstance(data["last_result"], dict):
            last_res = ExecutionResult.from_dict(data["last_result"])

        ctx = cls(
            session_id=data.get("session_id", "default"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            conversation_turn=data.get("conversation_turn", 0),
            active_application=data.get("active_application"),
            active_directory=data.get("active_directory"),
            active_file=data.get("active_file"),
            open_applications=list(data.get("open_applications", [])),
            active_entities=dict(data.get("active_entities", {})),
            history=[dict(h) for h in data.get("history", [])],
            last_result=last_res,
            last_error=data.get("last_error"),
            metadata=dict(data.get("metadata", {})),
            current_intent=curr_intent,
            previous_intent=prev_intent,
        )

        if restore_confirmation and data.get("pending_confirmation"):
            ctx.pending_confirmation = PendingConfirmation.from_dict(data["pending_confirmation"])

        return ctx
