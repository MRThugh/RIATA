"""
Context Manager for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)

Provides lifecycle management, session isolation, expiration,
and security-bound confirmation token tracking.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import TYPE_CHECKING, Any, Optional

from app.core.config import get_config
from app.core.context.models import PendingConfirmation, SessionContext
from app.core.logger import get_logger

if TYPE_CHECKING:
    from app.engine.intent import Intent

logger = get_logger("riata.context.manager")

# Maximum concurrent sessions to keep in memory to prevent memory exhaustion
MAX_SESSIONS = 100


class ContextManager:
    """
    Manages isolated conversational sessions, expiration, and confirmation flows.

    Thread-safe and bounded to ensure predictable memory characteristics.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, SessionContext] = {}

    def _load_session_from_disk(self, session_id: str) -> Optional[SessionContext]:
        try:
            import json
            from pathlib import Path
            clean_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
            target = Path("/tmp/riata_sessions") / f"{clean_id}.json"
            if target.is_file():
                raw = json.loads(target.read_text(encoding="utf-8"))
                return SessionContext.from_dict(raw)
        except Exception:
            pass
        return None

    def save_session(self, session_id: str = "default") -> None:
        """Persist session context to temp store for cross-process continuity."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx:
                return
            try:
                import json
                from pathlib import Path
                store_dir = Path("/tmp/riata_sessions")
                store_dir.mkdir(parents=True, exist_ok=True)
                clean_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
                target = store_dir / f"{clean_id}.json"
                target.write_text(json.dumps(ctx.to_dict()), encoding="utf-8")
            except Exception as e:
                logger.debug("Failed persisting session context '%s': %s", session_id, e)

    def get_or_create(self, session_id: str = "default") -> SessionContext:
        """Retrieve existing session context or initialize a new isolated session."""
        with self._lock:
            self._prune_expired()
            if session_id not in self._sessions:
                loaded = self._load_session_from_disk(session_id)
                if loaded:
                    self._sessions[session_id] = loaded
                    return loaded

                # Evict oldest session if limit exceeded
                if len(self._sessions) >= MAX_SESSIONS:
                    oldest_id = min(self._sessions, key=lambda k: self._sessions[k].updated_at)
                    logger.debug("Evicting oldest session '%s'", oldest_id)
                    del self._sessions[oldest_id]

                self._sessions[session_id] = SessionContext(
                    session_id=session_id,
                    created_at=time.time(),
                    updated_at=time.time(),
                )
            return self._sessions[session_id]

    def get_session(self, session_id: str = "default") -> Optional[SessionContext]:
        """Retrieve existing session context if present."""
        with self._lock:
            return self._sessions.get(session_id) or self._load_session_from_disk(session_id)

    def reset(self, session_id: str = "default") -> SessionContext:
        """Reset conversation context for a specific session."""
        with self._lock:
            try:
                from pathlib import Path
                clean_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
                target = Path("/tmp/riata_sessions") / f"{clean_id}.json"
                if target.exists():
                    target.unlink()
            except Exception:
                pass
            if session_id in self._sessions:
                self._sessions[session_id].clear()
                logger.info("Context reset for session '%s'", session_id)
                return self._sessions[session_id]
            return self.get_or_create(session_id)

    def reset_session(self, session_id: str = "default") -> SessionContext:
        """Alias for reset."""
        return self.reset(session_id)

    def set_pending_confirmation(
        self,
        session_id: str,
        intent: Intent,
        action_label: str = "",
        ttl: Optional[float] = None,
    ) -> PendingConfirmation:
        """
        Create a cryptographically distinct, session-bound pending confirmation token.
        """
        with self._lock:
            ctx = self.get_or_create(session_id)
            cfg = get_config()
            now = time.time()
            effective_ttl = ttl if ttl is not None else cfg.confirmation_lifetime
            expires_at = now + effective_ttl

            conf_id = f"conf-{int(now * 1000)}-{uuid.uuid4().hex[:8]}"
            pending = PendingConfirmation(
                confirmation_id=conf_id,
                session_id=session_id,
                action=intent.name,
                intent=intent,
                entities=dict(intent.entities),
                action_label=action_label or intent.name,
                created_at=now,
                expires_at=expires_at,
                status="PENDING",
            )
            ctx.pending_confirmation = pending
            logger.info(
                "Created pending confirmation '%s' for session '%s' (action: %s, expires in %.1fs)",
                conf_id,
                session_id,
                intent.name,
                effective_ttl,
            )
            return pending

    def get_pending_confirmation(self, session_id: str) -> Optional[PendingConfirmation]:
        """Retrieve active pending confirmation if still valid and unexpired."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx or not ctx.pending_confirmation:
                return None
            if not ctx.pending_confirmation.is_valid():
                ctx.pending_confirmation = None
                return None
            return ctx.pending_confirmation

    def consume_pending_confirmation(
        self,
        session_id: str,
        confirmation_id: Optional[str] = None,
    ) -> Optional[Intent]:
        """
        Consume and invalidate pending confirmation, returning the confirmed Intent.

        Ensures non-replayability: once consumed, it cannot be reused.
        """
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx or not ctx.pending_confirmation:
                return None

            conf = ctx.pending_confirmation
            if not conf.is_valid():
                ctx.pending_confirmation = None
                return None

            if confirmation_id and conf.confirmation_id != confirmation_id:
                logger.warning(
                    "Confirmation ID mismatch: expected %s, got %s",
                    conf.confirmation_id,
                    confirmation_id,
                )
                return None

            # Mark consumed and detach
            conf.status = "CONSUMED"
            confirmed_intent = conf.intent
            ctx.pending_confirmation = None
            logger.info("Successfully consumed confirmation '%s'", conf.confirmation_id)
            return confirmed_intent

    def reject_pending_confirmation(self, session_id: str) -> bool:
        """Cancel and invalidate pending confirmation."""
        with self._lock:
            ctx = self._sessions.get(session_id)
            if not ctx or not ctx.pending_confirmation:
                return False

            conf = ctx.pending_confirmation
            conf.status = "REJECTED"
            ctx.pending_confirmation = None
            logger.info("Rejected confirmation '%s'", conf.confirmation_id)
            return True

    def _prune_expired(self) -> None:
        """Internal prune of expired sessions based on configured context lifetime."""
        cfg = get_config()
        now = time.time()
        expired_ids = [
            sid
            for sid, ctx in self._sessions.items()
            if (now - ctx.updated_at) > cfg.context_lifetime
        ]
        for sid in expired_ids:
            logger.debug("Pruning expired session '%s'", sid)
            del self._sessions[sid]

    def clear_all(self) -> None:
        """Clear all active sessions (primarily for testing)."""
        with self._lock:
            self._sessions.clear()


_GLOBAL_CONTEXT_MANAGER: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Retrieve global ContextManager singleton."""
    global _GLOBAL_CONTEXT_MANAGER
    if _GLOBAL_CONTEXT_MANAGER is None:
        _GLOBAL_CONTEXT_MANAGER = ContextManager()
    return _GLOBAL_CONTEXT_MANAGER
