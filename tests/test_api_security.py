"""
Unit tests for ExecutionResult status codes, honest reporting, and security boundaries.
Author: Ali Kamrani (MRThugh)
"""

import pytest
from pathlib import Path

from app.core.config import get_config
from app.engine.intent import Intent
from app.engine.router import get_intent_router
from app.executor.files import execute_open_file
from app.executor.result import (
    STATUS_FAILED,
    STATUS_INVALID_COMMAND,
    STATUS_PATH_NOT_ALLOWED,
    STATUS_PERMISSION_DENIED,
    STATUS_SUCCESS,
    ExecutionResult,
)


@pytest.fixture
def router():
    return get_intent_router()


def test_execution_result_serialization():
    """Verify ExecutionResult to_dict includes all security audit fields."""
    res = ExecutionResult(
        success=True,
        executed=True,
        status=STATUS_SUCCESS,
        message="Launched application",
        intent_name="OPEN_APPLICATION",
        action_summary="Launched /usr/bin/firefox",
        data={"pid": 1234},
    )
    d = res.to_dict()
    assert d["success"] is True
    assert d["executed"] is True
    assert d["status"] == STATUS_SUCCESS
    assert d["message"] == "Launched application"
    assert d["data"] == {"pid": 1234}


def test_open_file_security_statuses():
    """Verify execute_open_file returns accurate honest statuses without crashing."""
    # 1. Path traversal outside sandbox
    intent_traversal = Intent(
        name="OPEN_FILE",
        confidence=0.95,
        entities={"file": "/etc/passwd"},
    )
    res_traversal = execute_open_file(intent_traversal)
    assert res_traversal.success is False
    assert res_traversal.executed is False
    assert res_traversal.status == STATUS_PATH_NOT_ALLOWED

    # 2. Non-existent file inside sandbox
    intent_missing = Intent(
        name="OPEN_FILE",
        confidence=0.95,
        entities={"file": "~/nonexistent_file_abc_123.txt"},
    )
    res_missing = execute_open_file(intent_missing)
    assert res_missing.success is False
    assert res_missing.executed is False
    assert res_missing.status == STATUS_FAILED

    # 3. Missing file entity
    intent_empty = Intent(
        name="OPEN_FILE",
        confidence=0.95,
        entities={},
    )
    res_empty = execute_open_file(intent_empty)
    assert res_empty.success is False
    assert res_empty.executed is False
    assert res_empty.status == STATUS_INVALID_COMMAND

    # 4. Sensitive credential file
    intent_sensitive = Intent(
        name="OPEN_FILE",
        confidence=0.95,
        entities={"file": "~/.ssh/id_rsa"},
    )
    res_sensitive = execute_open_file(intent_sensitive)
    assert res_sensitive.success is False
    assert res_sensitive.executed is False
    assert res_sensitive.status == STATUS_PATH_NOT_ALLOWED



def test_dangerous_intent_status_in_router(router):
    """Verify router returns STATUS_PERMISSION_DENIED with executed=False on dangerous input."""
    out = router.process("sudo rm -rf /")
    assert out.result.success is False
    assert out.result.executed is False
    assert out.result.status == STATUS_PERMISSION_DENIED
    assert out.intent.is_dangerous is True


def test_unknown_intent_status_in_router(router):
    """Verify router returns STATUS_INVALID_COMMAND with executed=False on unknown input."""
    out = router.process("random unrecognizable gibberish 98765")
    assert out.result.success is False
    assert out.result.executed is False
    assert out.result.status == STATUS_INVALID_COMMAND
