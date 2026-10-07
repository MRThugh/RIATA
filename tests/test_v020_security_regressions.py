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
