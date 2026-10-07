"""
Tests for R.I.A.T.A v0.1.1 Desktop Capabilities Foundation.
Author: Ali Kamrani (MRThugh)

Verifies:
- Capability discovery & registration
- Intent routing to specialized capabilities
- Modular architecture separation
"""

import pytest
from app.capabilities.registry import get_capability_registry
from app.core.constants import INTENT_OPEN_APPLICATION, INTENT_OPEN_FOLDER, INTENT_PLAY_MUSIC
from app.engine.intent import Intent
from app.executor.result import STATUS_NOT_SUPPORTED


def test_capability_registry_discovery():
    registry = get_capability_registry()
    caps = registry.list_capabilities()
    cap_ids = [c.id for c in caps]

    assert "applications" in cap_ids
    assert "filesystem" in cap_ids
    assert "media" in cap_ids
    assert "system" in cap_ids
    assert "processes" in cap_ids
    assert "windows" in cap_ids
    assert "notifications" in cap_ids
    assert "clipboard" in cap_ids


def test_capability_intent_dispatch():
    registry = get_capability_registry()

    app_cap = registry.find_for_intent(INTENT_OPEN_APPLICATION)
    assert app_cap is not None
    assert app_cap.id == "applications"

    fs_cap = registry.find_for_intent(INTENT_OPEN_FOLDER)
    assert fs_cap is not None
    assert fs_cap.id == "filesystem"

    media_cap = registry.find_for_intent(INTENT_PLAY_MUSIC)
    assert media_cap is not None
    assert media_cap.id == "media"


def test_stubs_capabilities_clean_status():
    registry = get_capability_registry()

    proc_cap = registry.get_capability("processes")
    assert proc_cap is not None
    res = proc_cap.execute(Intent(name="LIST_PROCESSES", confidence=1.0))
    assert res.executed is False
    assert res.status == STATUS_NOT_SUPPORTED
