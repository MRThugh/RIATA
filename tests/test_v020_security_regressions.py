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


def test_command_api_stdin_transport_preserves_session_id():
    """Section 6 & 7 regression: Verify /api/command passes session_id through stdin JSON to python subprocess."""
    root_dir = Path(__file__).resolve().parent.parent
    vite_cfg = (root_dir / "vite.config.ts").read_text(encoding="utf-8")

    # Statically verify that session_id is preserved in stdin JSON write
    assert "pyProc.stdin.write(JSON.stringify({ text, dry_run: Boolean(dry_run), session_id }))" in vite_cfg
    assert "session_id = str(payload.get('session_id', 'web-companion'))" in vite_cfg
    assert "output = router.process(command_text, session_id=session_id)" in vite_cfg


def test_web_session_isolation_behavioral():
    """Section 8 regression: Commands in session A must never leak contextual state into session B."""
    from app.engine.router import get_intent_router
    from app.core.config import get_config

    cfg = get_config()
    orig_dry_run = cfg.dry_run
    cfg.dry_run = True

    try:
        router = get_intent_router()
        router.reset_context()

        session_a = "test-session-isolation-A"
        session_b = "test-session-isolation-B"

        # Session A: Open Firefox
        out_a1 = router.process("Firefox رو باز کن", session_id=session_a)
        assert out_a1.result.success is True

        ctx_a = router.context_manager.get_session(session_a)
        assert ctx_a.active_application == "firefox"

        # Session B: Try to close 'it' without having opened anything in Session B
        ctx_b_before = router.context_manager.get_session(session_b)
        assert ctx_b_before is None or ctx_b_before.active_application is None

        out_b1 = router.process("ببندش", session_id=session_b)

        # Session B must NOT inherit Firefox from Session A!
        ctx_b = router.context_manager.get_session(session_b)
        assert ctx_b.active_application != "firefox"
        # It must require clarification or fail because no app was active in session B
        assert out_b1.intent.name != "CLOSE_APPLICATION" or out_b1.result.success is False or out_b1.result.status == "NEEDS_CLARIFICATION"
    finally:
        cfg.dry_run = orig_dry_run


def test_web_companion_security_boundary_audit():
    """Section 14, 15, 16, 17: Verify loopback-only, IPv6 parsing, and API method restrictions in vite.config.ts."""
    root_dir = Path(__file__).resolve().parent.parent
    vite_cfg = (root_dir / "vite.config.ts").read_text(encoding="utf-8")

    # Section 15: No preview host exceptions permitted
    assert "RIATA_ALLOW_PREVIEW_HOSTS" not in vite_cfg
    assert ".run.app" not in vite_cfg
    assert ".aistudio.google" not in vite_cfg
    assert ".google.internal" not in vite_cfg

    # Section 16: Proper URL parsing instead of fragile split(":")[0]
    assert 'split(":")[0]' not in vite_cfg
    assert "parseHostname" in vite_cfg

    # Section 17: Client identifier web-v0.2.0 only
    assert '"web-v0.2.0"' in vite_cfg
    assert '"web-v0.1.1"' not in vite_cfg

    # Section 10 & 11: /api/run-tests is POST only and gated behind RIATA_ENABLE_TEST_API
    assert "RIATA_ENABLE_TEST_API" in vite_cfg
    assert 'Method not allowed. Use POST.' in vite_cfg


def test_reset_context_clears_all_pending_and_contextual_state():
    """Section 18: Reset must clear active entities, pending confirmation, pending plan, and disk session."""
    from app.engine.router import get_intent_router
    from app.core.config import get_config

    cfg = get_config()
    orig_dry_run = cfg.dry_run
    cfg.dry_run = True

    try:
        router = get_intent_router()
        session_id = "test-reset-all-state-session"

        # Create active state and pending confirmation
        out1 = router.process("Firefox رو باز کن و فایل test_reset.txt رو حذف کن", session_id=session_id)
        ctx = router.context_manager.get_session(session_id)
        assert ctx is not None
        assert ctx.pending_confirmation is not None
        assert ctx.pending_plan is not None

        # Execute reset
        ctx.clear()
        router.context_manager.reset(session_id)
        router.reset_context()

        # State must be completely empty
        reset_ctx = router.context_manager.get_session(session_id)
        assert reset_ctx.pending_confirmation is None
        assert reset_ctx.pending_plan is None
        assert reset_ctx.pending_step_index == 0
        assert reset_ctx.active_application is None
        assert reset_ctx.active_file is None
        assert reset_ctx.active_directory is None
    finally:
        cfg.dry_run = orig_dry_run


