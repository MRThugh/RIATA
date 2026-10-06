"""
Security regression tests for command execution, injection prevention, and allowlist policies.
Author: Ali Kamrani (MRThugh)
"""

import pytest

from app.core.config import get_config
from app.core.constants import DANGEROUS_COMMANDS
from app.engine.router import get_intent_router
from app.executor.result import STATUS_APP_NOT_FOUND, STATUS_PERMISSION_DENIED
from app.registry.applications import get_application_registry


@pytest.fixture
def router():
    return get_intent_router()


def test_shell_injection_payloads_never_executed(router):
    """
    SHELL INJECTION NEGATIVE TEST:
    Verify that classic shell metacharacters and command injection payloads
    are caught or never evaluated as executable shell commands.
    """
    injection_payloads = [
        "$(whoami)",
        "`whoami`",
        "; rm -rf /",
        "&& whoami",
        "|| whoami",
        "| whoami",
        "$(touch /tmp/pwned)",
        "open firefox; whoami",
        "firefox && rm -rf ~",
        "test | ls -la",
        "> /dev/sda",
        ":(){ :|:& };:",
    ]

    for payload in injection_payloads:
        out = router.process(payload)
        # Must NEVER be executed on the host OS
        assert out.result.executed is False, f"Payload was executed: {payload}"
        # If recognized as dangerous or blocked
        if out.intent.is_dangerous:
            assert out.result.status == STATUS_PERMISSION_DENIED


def test_dangerous_commands_list_coverage(router):
    """Verify all defined dangerous commands are blocked."""
    for cmd in DANGEROUS_COMMANDS:
        out = router.process(cmd)
        assert out.result.executed is False
        assert out.intent.is_dangerous is True
        assert out.result.status == STATUS_PERMISSION_DENIED


def test_safe_execution_policy_semantics():
    """
    SAFE_EXECUTION CONFIGURATION SEMANTICS TEST:
    - When safe_execution=True: strict application allowlist. Unknown binaries in PATH
      not in the registered catalog must NOT be returned.
    - When safe_execution=False: allows non-dangerous installed binaries in PATH,
      while STILL strictly rejecting dangerous commands (rm, sudo, etc.).
    """
    config = get_config()
    registry = get_application_registry()

    # 1. Test with safe_execution = True (Strict Allowlist)
    config.safe_execution = True
    # 'python3' is a real binary in PATH but not in desktop allowlist
    assert registry.find("python3", safe_execution=True) is None

    # Registered app works
    assert registry.find("firefox", safe_execution=True) is not None

    # Dangerous command is blocked
    assert registry.find("rm", safe_execution=True) is None
    assert registry.find("sudo", safe_execution=True) is None

    # 2. Test with safe_execution = False (Relaxed Allowlist)
    config.safe_execution = False
    try:
        # Non-dangerous binary in PATH is now permitted
        entry = registry.find("python3", safe_execution=False)
        assert entry is not None
        assert entry.command == "python3"

        # DANGEROUS COMMANDS MUST STILL BE BLOCKED even when safe_execution=False!
        assert registry.find("rm", safe_execution=False) is None
        assert registry.find("sudo", safe_execution=False) is None
        assert registry.find("shutdown", safe_execution=False) is None
        assert registry.find("mkfs", safe_execution=False) is None
    finally:
        config.safe_execution = True


def test_executed_flag_accuracy(router):
    """
    HONEST EXECUTION REPORTING:
    Verify that executed=True is ONLY returned when an actual process was spawned,
    and is False for dry-run, missing apps, blocked commands, and failed actions.
    """
    config = get_config()

    # Dry-run: success=True, but executed=False
    config.dry_run = True
    try:
        out = router.process("Open Firefox")
        assert out.result.executed is False
        assert out.result.is_dry_run is True
    finally:
        config.dry_run = False

    # Blocked dangerous command: executed=False
    out_danger = router.process("sudo rm -rf /")
    assert out_danger.result.executed is False
    assert out_danger.result.status == STATUS_PERMISSION_DENIED

    # Unknown command: executed=False
    out_unknown = router.process("nonexistent_command_12345")
    assert out_unknown.result.executed is False
