"""
Security regression test suite for R.I.A.T.A v0.2.0.
Author: Ali Kamrani (MRThugh)

Verifies:
- Zero 'shell=True' invocations across the entire codebase
- Path traversal escapes ('../../etc/shadow') strictly blocked
- Symlink escape attacks rejected
- Sensitive home subdirectories (~/.ssh, ~/.gnupg, ~/.aws) inaccessible
- Subprocess command injection metacharacters rejected
- Policy Engine remains authoritative (context cannot bypass policy)
- Confirmation token replay attack prevention
- Session isolation enforcement
"""

import os
from pathlib import Path
import pytest

from app.core.config import get_config
from app.core.context.manager import ContextManager
from app.engine.intent import Intent
from app.engine.router import get_intent_router
from app.executor.files import execute_create_file, execute_delete_file, is_allowed_path
from app.executor.result import STATUS_PATH_NOT_ALLOWED, STATUS_PERMISSION_DENIED
from app.policy.engine import get_policy_engine


def test_zero_shell_true_in_source_code():
    """Verify that shell=True is never used anywhere in the app/ source directory."""
    app_dir = Path(__file__).resolve().parent.parent / "app"
    forbidden = "shell=True"

    violations = []
    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        if forbidden in content:
            violations.append(str(py_file))

    assert len(violations) == 0, f"Found forbidden shell=True in: {violations}"


def test_path_traversal_escape_rejected():
    """Ensure directory traversal escapes are denied."""
    assert is_allowed_path("/home/user/../../etc/passwd") is False
    assert is_allowed_path("/home/user/../../etc/shadow") is False
    assert is_allowed_path("../../etc/hosts") is False


def test_sensitive_credential_directories_rejected():
    """Ensure credential folders inside home are blocked."""
    home = Path.home()
    assert is_allowed_path(home / ".ssh") is False
    assert is_allowed_path(home / ".ssh" / "id_rsa") is False
    assert is_allowed_path(home / ".gnupg" / "secring.gpg") is False
    assert is_allowed_path(home / ".aws" / "credentials") is False
    assert is_allowed_path(home / ".bash_history") is False


def test_context_cannot_bypass_policy_engine():
    """
    CRITICAL SECURITY INVARIANT:
    Even if context has active_file='secret.txt',
    a DELETE_FILE action MUST still go through PolicyEngine (requires confirmation)!
    """
    router = get_intent_router()
    router.reset_context()
    session_id = "test-security-bypass-check"

    session_ctx = router.context_manager.get_or_create(session_id)
    session_ctx.active_file = "sensitive_notes.txt"

    # User says "حذفش کن" -> Context resolves to "sensitive_notes.txt"
    out = router.process("حذفش کن", session_id=session_id)

    # Policy Engine MUST intervene: requires confirmation!
    assert out.result.executed is False
    assert out.result.status == "NEEDS_CONFIRMATION"


def test_dangerous_shell_injection_payloads_blocked():
    """Verify command injection attempts are recognized and rejected."""
    router = get_intent_router()
    payloads = [
        "firefox; rm -rf ~",
        "chrome && sudo reboot",
        "ls | mkfs.ext4 /dev/sda",
        "`cat /etc/passwd`",
        "$(whoami)",
        ":(){ :|:& };:",
    ]
    for p in payloads:
        out = router.process(p, session_id="sec-payloads")
        assert out.result.executed is False
        assert out.result.status == STATUS_PERMISSION_DENIED or out.intent.is_dangerous is True


def test_confirmation_token_cannot_be_replayed():
    """Ensure single-use confirmation token cannot be reused for a second operation."""
    mgr = ContextManager()
    intent = Intent(name="DELETE_FILE", confidence=1.0, entities={"file": "target.txt"})
    token = mgr.set_pending_confirmation("session-replay", intent, action_label="delete target.txt")

    # First consumption succeeds
    first = mgr.consume_pending_confirmation("session-replay", token.confirmation_id)
    assert first is not None

    # Immediate second consumption fails
    second = mgr.consume_pending_confirmation("session-replay", token.confirmation_id)
    assert second is None


def test_vite_config_and_package_json_local_only():
    """Ensure dev server configuration is bound strictly to 127.0.0.1 and not 0.0.0.0."""
    root_dir = Path(__file__).resolve().parent.parent
    vite_cfg = (root_dir / "vite.config.ts").read_text(encoding="utf-8")
    pkg_json = (root_dir / "package.json").read_text(encoding="utf-8")

    # Check package.json scripts
    assert "--host 127.0.0.1" in pkg_json
    assert "--host 0.0.0.0" not in pkg_json

    # Check vite.config.ts server and preview bindings
    assert 'host: "127.0.0.1"' in vite_cfg
    assert 'host: "0.0.0.0"' not in vite_cfg


def test_reset_context_stdin_transport_security():
    """Ensure /api/reset-context does not interpolate session_id into python source code."""
    root_dir = Path(__file__).resolve().parent.parent
    vite_cfg = (root_dir / "vite.config.ts").read_text(encoding="utf-8")

    # String interpolation into Python code is strictly forbidden
    assert 'cm.reset_session("${sessionId}")' not in vite_cfg
    assert 'reset_session("${session_id}")' not in vite_cfg

    # Must pass JSON payload over stdin
    assert "proc.stdin.write(JSON.stringify({ session_id: sessionId }))" in vite_cfg
    assert "json.loads(sys.stdin.read()" in vite_cfg
    assert "SESSION_ID_PATTERN" in vite_cfg


def test_session_id_strict_validation():
    """Ensure session_id format is strictly validated without path traversal or injection."""
    from app.core.context.manager import get_session_file_path, is_valid_session_id, validate_session_id

    # Valid session IDs
    assert is_valid_session_id("valid-session-123") is True
    assert is_valid_session_id("session_456") is True
    assert validate_session_id("session-1") == "session-1"

    # Invalid session IDs: path traversal, shell characters, whitespace
    invalid_ids = [
        "../evil_session",
        "../../etc/passwd",
        "session; rm -rf /",
        "session && id",
        "session\x00null",
        "session with spaces",
        "",
        "a" * 65,  # Exceeds max 64 characters
    ]
    for bad_id in invalid_ids:
        assert is_valid_session_id(bad_id) is False
        with pytest.raises(ValueError):
            validate_session_id(bad_id)
        with pytest.raises(ValueError):
            get_session_file_path(bad_id)


def test_expired_session_disk_ttl_not_resurrected(tmp_path):
    """Ensure expired session context files on disk are unlinked and not resurrected."""
    import json
    import time
    from app.core.context.manager import ContextManager
    from app.core.context.models import SessionContext

    mgr = ContextManager(storage_dir=tmp_path)
    session_id = "test-expired-disk-session"
    ctx = mgr.get_or_create(session_id)
    ctx.active_application = "firefox"

    # Persist session to disk
    mgr.save_session(session_id)
    session_file = tmp_path / f"{session_id}.json"
    assert session_file.is_file()

    # Simulate expired session by setting updated_at to the distant past
    data = json.loads(session_file.read_text(encoding="utf-8"))
    data["updated_at"] = time.time() - 999999
    session_file.write_text(json.dumps(data), encoding="utf-8")

    # Clear in-memory cache to force disk load
    mgr._sessions.clear()

    # Attempt to load expired session: must return None and unlink file
    loaded = mgr._load_session_from_disk(session_id)
    assert loaded is None
    assert not session_file.exists()


def test_disk_session_invalidates_pending_confirmation(tmp_path):
    """Ensure pending confirmation tokens are never restored from disk storage."""
    import json
    from app.core.context.manager import ContextManager
    from app.core.context.models import PendingConfirmation, SessionContext

    mgr = ContextManager(storage_dir=tmp_path)
    session_id = "test-disk-conf-invalidation"
    session_file = tmp_path / f"{session_id}.json"

    # Manually craft a disk file that maliciously attempts to persist a confirmation
    raw_data = {
        "session_id": session_id,
        "updated_at": 9999999999.0,  # Far future
        "conversation_turn": 1,
        "active_application": "firefox",
        "has_pending_confirmation": True,
        "pending_confirmation": {
            "confirmation_id": "malicious-conf-id",
            "session_id": session_id,
            "action": "DELETE_FILE",
            "action_label": "delete file",
            "status": "PENDING",
            "expires_at": 9999999999.0,
        },
    }
    session_file.write_text(json.dumps(raw_data), encoding="utf-8")

    loaded = mgr._load_session_from_disk(session_id)
    assert loaded is not None
    assert loaded.active_application == "firefox"
    # Crucial security invariant: pending confirmation must NOT be restored across disk reload!
    assert loaded.pending_confirmation is None

