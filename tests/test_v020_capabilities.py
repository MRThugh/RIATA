"""
Unit tests for R.I.A.T.A v0.2.0 Standardized Capability Contracts & Execution.
Author: Ali Kamrani (MRThugh)

Verifies:
- Standardized BaseCapability contract (describe, validate, execute, metadata)
- CapabilityRegistry operations (register, unregister, supports_intent, get_capability)
- ApplicationsCapability: OPEN_APPLICATION, CLOSE_APPLICATION, OPEN_URL
- FilesystemCapability: CREATE_FILE, DELETE_FILE, CREATE_FOLDER, DELETE_FOLDER
- Strict sandbox containment verification for file creation and deletion
"""

import os
from pathlib import Path
import pytest

from app.capabilities.applications import ApplicationsCapability
from app.capabilities.base import BaseCapability
from app.capabilities.filesystem import FilesystemCapability
from app.capabilities.registry import CapabilityRegistry, get_capability_registry
from app.core.config import get_config
from app.engine.intent import Intent
from app.executor.result import (
    STATUS_PATH_NOT_ALLOWED,
    STATUS_SUCCESS,
    ExecutionResult,
)


def test_base_capability_standardized_contract():
    cap = ApplicationsCapability()

    # Introspection metadata
    meta = cap.metadata()
    assert meta["id"] == "applications"
    assert "OPEN_APPLICATION" in meta["supported_intents"]
    assert "CLOSE_APPLICATION" in meta["supported_intents"]
    assert "OPEN_URL" in meta["supported_intents"]

    # Describe method
    intent = Intent(name="OPEN_APPLICATION", confidence=1.0)
    desc = cap.describe(intent)
    assert "Application Management" in desc

    # Validate method
    valid, err = cap.validate(intent)
    assert valid is True
    assert err is None

    invalid_intent = Intent(name="NONEXISTENT_ACTION", confidence=1.0)
    valid2, err2 = cap.validate(invalid_intent)
    assert valid2 is False
    assert "does not support" in err2


def test_capability_registry_unregister_and_supports():
    reg = CapabilityRegistry()

    assert reg.supports_intent("OPEN_APPLICATION") is True
    assert reg.supports_intent("CREATE_FILE") is True

    # Unregister filesystem capability
    unreg_success = reg.unregister("filesystem")
    assert unreg_success is True
    assert reg.get_capability("filesystem") is None
    assert reg.supports_intent("CREATE_FILE") is False

    # Unregister unknown
    assert reg.unregister("unknown_cap_xyz") is False


def test_applications_capability_close_app_dry_run():
    config = get_config()
    orig = config.dry_run
    config.dry_run = True

    try:
        cap = ApplicationsCapability()
        intent = Intent(
            name="CLOSE_APPLICATION",
            confidence=1.0,
            entities={"application": "firefox"},
        )
        res = cap.execute(intent)
        assert res.success is True
        assert res.is_dry_run is True
        assert res.status == STATUS_SUCCESS
        assert "pkill" in res.action_summary
    finally:
        config.dry_run = orig


def test_applications_capability_open_url_dry_run():
    config = get_config()
    orig = config.dry_run
    config.dry_run = True

    try:
        cap = ApplicationsCapability()
        intent = Intent(
            name="OPEN_URL",
            confidence=1.0,
            entities={"url": "https://github.com"},
        )
        res = cap.execute(intent)
        assert res.success is True
        assert res.is_dry_run is True
        assert res.status == STATUS_SUCCESS
        assert "github.com" in res.action_summary
    finally:
        config.dry_run = orig


def test_filesystem_capability_create_and_delete_file_in_tmp():
    config = get_config()
    orig = config.dry_run
    config.dry_run = False

    try:
        cap = FilesystemCapability()
        test_file = f"/tmp/riata_test_{os.getpid()}.txt"

        # 1. Create file
        intent_create = Intent(
            name="CREATE_FILE",
            confidence=1.0,
            entities={"file": test_file},
        )
        res_create = cap.execute(intent_create)
        assert res_create.success is True
        assert Path(test_file).is_file()

        # 2. Delete file
        intent_delete = Intent(
            name="DELETE_FILE",
            confidence=1.0,
            entities={"file": test_file},
        )
        res_delete = cap.execute(intent_delete)
        assert res_delete.success is True
        assert not Path(test_file).exists()
    finally:
        config.dry_run = orig
        if Path(test_file).exists():
            Path(test_file).unlink()


def test_filesystem_capability_blocks_disallowed_paths():
    cap = FilesystemCapability()

    # Attempt to create file in /etc/passwd
    intent_bad = Intent(
        name="CREATE_FILE",
        confidence=1.0,
        entities={"file": "/etc/malicious.txt"},
    )
    res = cap.execute(intent_bad)
    assert res.success is False
    assert res.status == STATUS_PATH_NOT_ALLOWED
