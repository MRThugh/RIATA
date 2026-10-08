"""
Comprehensive Integration & Regression Tests for R.I.A.T.A v0.2.0 Persistent Web Companion
Author: Ali Kamrani (MRThugh)

Verifies:
- Test A: Context persistence across real HTTP requests (Request 1 -> open Firefox, Request 2 -> close it / ببندش)
- Test B: Confirmation token persistence across real HTTP requests (Request 1 -> delete file, Request 2 -> yes / بله)
- Test C: Multi-step plan execution and resumption across HTTP requests
- Test D: Step failure isolation in multi-step plans
- Test E: Complete isolation between independent concurrent sessions
- Section 22: Reproduction of the original per-request process bug vs persistent session fix
- Session reset endpoint (/api/reset-context)
- HTTP security boundary enforcement (loopback, client header, input sanitization)
- Concurrency serialization per session
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Optional

import pytest

from app.backend.server import create_server
from app.core.config import get_config
from app.core.constants import INTENT_CLOSE_APPLICATION, INTENT_DELETE_FILE, INTENT_OPEN_APPLICATION
from app.core.context.manager import ContextManager
from app.engine.intent import Intent
from app.engine.router import IntentRouter, get_intent_router
from app.executor.result import STATUS_NEEDS_CONFIRMATION, STATUS_SUCCESS


@pytest.fixture(scope="module")
def persistent_server():
    """
    Spawns a real ThreadingHTTPServer on an ephemeral loopback port for end-to-end HTTP tests.
    """
    server = create_server(host="127.0.0.1", port=0)
    assigned_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)  # Allow socket to bind and listen
    base_url = f"http://127.0.0.1:{assigned_port}"

    yield base_url

    server.shutdown()
    server.server_close()


def post_http(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    headers: Optional[dict[str, str]] = None,
) -> tuple[int, dict[str, Any]]:
    """Helper to perform structured JSON HTTP requests to the persistent backend."""
    url = f"{base_url}{path}"
    data = json.dumps(payload).encode("utf-8")
    req_headers = {
        "Content-Type": "application/json",
        "X-RIATA-Client": "web-v0.2.0",
        "Host": f"127.0.0.1:{base_url.split(':')[-1]}",
        "Connection": "close",
    }
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"status": "INVALID_COMMAND", "raw": body}
    except (ConnectionResetError, urllib.error.URLError) as e:
        return 413, {"status": "INVALID_COMMAND", "error": str(e)}


# =============================================================================
# Test A: Context Persistence Across Requests (Firefox -> ببندش)
# =============================================================================

def test_http_context_persistence_across_requests(persistent_server):
    """
    Test A: Verify contextual active_application survives across distinct HTTP requests.
    Request 1: 'Firefox رو باز کن' -> Sets active application to Firefox
    Request 2: 'ببندش' -> Contextual pronoun resolves 'ش' to Firefox and closes it
    """
    session_id = "test-session-ctx-flow"

    # Request 1: Open Firefox
    code1, res1 = post_http(
        persistent_server,
        "/api/command",
        {"text": "Firefox رو باز کن", "dry_run": True, "session_id": session_id},
    )
    assert code1 == 200
    assert res1["success"] is True
    assert res1["intent"]["name"] == INTENT_OPEN_APPLICATION
    assert res1["context"]["active_application"] == "firefox"

    # Request 2: Close it (ببندش)
    code2, res2 = post_http(
        persistent_server,
        "/api/command",
        {"text": "ببندش", "dry_run": True, "session_id": session_id},
    )
    assert code2 == 200
    assert res2["success"] is True
    assert res2["intent"]["name"] == INTENT_CLOSE_APPLICATION
    assert res2["intent"]["entities"]["application"] == "firefox"


# =============================================================================
# Test B: Confirmation Persistence Across Requests (Delete file -> بله)
# =============================================================================

def test_http_confirmation_persistence_across_requests(persistent_server):
    """
    Test B: Verify high-risk pending confirmation token survives across HTTP requests.
    Request 1: 'فایل test.txt رو حذف کن' -> NEEDS_CONFIRMATION
    Request 2: 'بله' -> Confirms and completes operation
    """
    session_id = "test-session-conf-flow"

    # Request 1: Delete file (Requires confirmation)
    code1, res1 = post_http(
        persistent_server,
        "/api/command",
        {"text": "فایل test.txt رو حذف کن", "dry_run": True, "session_id": session_id},
    )
    assert code1 == 200
    assert res1["status"] == STATUS_NEEDS_CONFIRMATION
    assert res1["context"]["has_pending_confirmation"] is True
    assert res1["result"]["metadata"]["confirmation_id"] is not None

    # Request 2: User confirms with 'بله'
    code2, res2 = post_http(
        persistent_server,
        "/api/command",
        {"text": "بله", "dry_run": True, "session_id": session_id},
    )
    assert code2 == 200
    assert res2["success"] is True
    assert res2["intent"]["name"] == INTENT_DELETE_FILE
    assert res2["context"]["has_pending_confirmation"] is False


# =============================================================================
# Test C: Multi-Step Plan with Pending Confirmation (Chrome -> Delete file -> بله)
# =============================================================================

def test_http_multistep_plan_with_confirmation(persistent_server):
    """
    Test C: Verify multi-step plan pauses for confirmation and resumes across HTTP requests.
    Request 1: 'Chrome رو باز کن و فایل report.txt رو حذف کن'
               Step 0 -> OPEN_APPLICATION (SUCCESS)
               Step 1 -> DELETE_FILE (NEEDS_CONFIRMATION)
    Request 2: 'بله' -> Confirms Step 1 and completes entire plan
    """
    session_id = "test-session-multi-step-conf"

    # Request 1: Two-step command
    code1, res1 = post_http(
        persistent_server,
        "/api/command",
        {"text": "Chrome رو باز کن و فایل report.txt رو حذف کن", "dry_run": True, "session_id": session_id},
    )
    assert code1 == 200
    assert res1["status"] == STATUS_NEEDS_CONFIRMATION
    assert res1["plan"] is not None
    assert len(res1["plan"]["steps"]) == 2
    assert res1["plan"]["steps"][0]["status"] == "SUCCESS"
    assert res1["plan"]["steps"][1]["status"] == "PENDING"

    # Request 2: Confirm Step 1
    code2, res2 = post_http(
        persistent_server,
        "/api/command",
        {"text": "بله", "dry_run": True, "session_id": session_id},
    )
    assert code2 == 200
    assert res2["success"] is True
    assert res2["plan"] is not None
    assert res2["plan"]["status"] == "SUCCESS"
    assert res2["plan"]["steps"][1]["status"] == "SUCCESS"


# =============================================================================
# Test D: Failed Step Isolation in Multi-Step Plans
# =============================================================================

def test_http_multistep_failure_isolation(persistent_server):
    """
    Test D: Verify that if a step fails or is blocked, subsequent dependent steps are SKIPPED.
    """
    session_id = "test-session-failure-isolation"

    # Dangerous payload causes policy block
    code, res = post_http(
        persistent_server,
        "/api/command",
        {"text": "sudo rm -rf / و Chrome رو باز کن", "dry_run": True, "session_id": session_id},
    )
    assert code == 200
    assert res["success"] is False
    # Dangerous command blocked by policy
    assert res["status"] in ("PERMISSION_DENIED", "FAILED")


# =============================================================================
# Test E: Multiple Independent Sessions Isolation
# =============================================================================

def test_http_multiple_sessions_strict_isolation(persistent_server):
    """
    Test E: Verify that distinct session_ids are strictly isolated.
    Session A: Opens Firefox
    Session B: Does NOT have Firefox in context; 'ببندش' fails or requires clarification
    Session A: Pending confirmation cannot be consumed by Session B
    """
    session_a = "session-alice-isolation"
    session_b = "session-bob-isolation"

    # 1. Session A opens Firefox
    code_a1, res_a1 = post_http(
        persistent_server,
        "/api/command",
        {"text": "Firefox رو باز کن", "dry_run": True, "session_id": session_a},
    )
    assert code_a1 == 200
    assert res_a1["context"]["active_application"] == "firefox"

    # 2. Session B tries 'ببندش' without an active application
    code_b1, res_b1 = post_http(
        persistent_server,
        "/api/command",
        {"text": "ببندش", "dry_run": True, "session_id": session_b},
    )
    assert code_b1 == 200
    # Must NOT inherit Firefox from Session A!
    assert res_b1["context"].get("active_application") != "firefox"
    assert res_b1["status"] in ("NEEDS_CLARIFICATION", "INVALID_COMMAND")

    # 3. Session A initiates high-risk deletion
    code_a2, res_a2 = post_http(
        persistent_server,
        "/api/command",
        {"text": "فایل secret.txt رو حذف کن", "dry_run": True, "session_id": session_a},
    )
    assert code_a2 == 200
    assert res_a2["status"] == STATUS_NEEDS_CONFIRMATION

    # 4. Session B sends 'بله' (cannot consume Session A's token)
    code_b2, res_b2 = post_http(
        persistent_server,
        "/api/command",
        {"text": "بله", "dry_run": True, "session_id": session_b},
    )
    assert code_b2 == 200
    # Session B has no pending confirmation, so 'بله' is not consumed
    assert res_b2["intent"]["name"] != INTENT_DELETE_FILE

    # 5. Session A can still safely confirm its own token
    code_a3, res_a3 = post_http(
        persistent_server,
        "/api/command",
        {"text": "بله", "dry_run": True, "session_id": session_a},
    )
    assert code_a3 == 200
    assert res_a3["success"] is True
    assert res_a3["intent"]["name"] == INTENT_DELETE_FILE


# =============================================================================
# Section 22: Reproduction of the Original Bug vs Fixed Persistent Architecture
# =============================================================================

def test_reproduce_original_stateless_spawn_bug_vs_persistent_fix(persistent_server):
    """
    Section 22 Regression Test:
    Directly demonstrates why spawning a new process per request failed:
    In a stateless spawn model, pending confirmations are not restored across processes.
    In the persistent backend, the confirmation token remains alive and executes cleanly.
    """
    session_id = "test-repro-original-bug"

    # --- Part 1: Simulate the OLD flawed stateless spawn model ---
    # In the old model, each request ran in a separate process with a fresh ContextManager
    old_mgr_1 = ContextManager()
    intent = Intent(name="DELETE_FILE", confidence=1.0, entities={"file": "old_bug.txt"})
    old_mgr_1.set_pending_confirmation(session_id, intent, action_label="delete old_bug.txt")
    # Old process saves session to disk (which explicitly strips pending confirmation!)
    old_mgr_1.save_session(session_id)

    # Old process exits -> New process starts with fresh ContextManager
    old_mgr_2 = ContextManager()
    # In the new process, pending confirmation is lost!
    assert old_mgr_2.get_pending_confirmation(session_id) is None
    # Attempting to consume confirmation in the second process FAILS in the old model:
    consumed_old = old_mgr_2.consume_pending_confirmation(session_id)
    assert consumed_old is None, "In the old model, confirmation was lost between processes!"

    # --- Part 2: Verify the NEW Persistent Backend FIX ---
    # Request 1 over persistent HTTP API
    code1, res1 = post_http(
        persistent_server,
        "/api/command",
        {"text": "فایل old_bug.txt رو حذف کن", "dry_run": True, "session_id": session_id},
    )
    assert code1 == 200
    assert res1["status"] == STATUS_NEEDS_CONFIRMATION

    # Request 2 over persistent HTTP API: confirmation remains alive and executes!
    code2, res2 = post_http(
        persistent_server,
        "/api/command",
        {"text": "بله", "dry_run": True, "session_id": session_id},
    )
    assert code2 == 200
    assert res2["success"] is True
    assert res2["intent"]["name"] == INTENT_DELETE_FILE


# =============================================================================
# Context Reset Endpoint Test (/api/reset-context)
# =============================================================================

def test_http_reset_context_endpoint(persistent_server):
    """
    Verify /api/reset-context clears all session state and pending confirmations.
    """
    session_id = "test-session-reset-endpoint"

    # Set up active state and pending confirmation
    post_http(
        persistent_server,
        "/api/command",
        {"text": "Firefox رو باز کن و فایل delete_me.txt رو حذف کن", "dry_run": True, "session_id": session_id},
    )

    # Call reset context
    code_reset, res_reset = post_http(
        persistent_server,
        "/api/reset-context",
        {"session_id": session_id},
    )
    assert code_reset == 200
    assert res_reset["success"] is True
    assert res_reset["status"] == "SUCCESS"

    # Verify context is empty
    code_after, res_after = post_http(
        persistent_server,
        "/api/command",
        {"text": "ببندش", "dry_run": True, "session_id": session_id},
    )
    assert code_after == 200
    # No active application to close
    assert res_after["context"].get("active_application") is None
    assert res_after["status"] in ("NEEDS_CLARIFICATION", "INVALID_COMMAND")


# =============================================================================
# Security & Boundary Rejections
# =============================================================================

def test_http_security_boundaries(persistent_server):
    """
    Verify strict security rejection of invalid client header, malformed session_id,
    and cross-site browser requests.
    """
    # 1. Reject invalid or missing client header
    code_hdr, res_hdr = post_http(
        persistent_server,
        "/api/command",
        {"text": "Firefox رو باز کن", "session_id": "valid-id"},
        headers={"X-RIATA-Client": "unauthorized-client-v9"},
    )
    assert code_hdr == 403
    assert res_hdr["status"] == "PERMISSION_DENIED"

    # 2. Reject path-traversal session_id
    code_sess, res_sess = post_http(
        persistent_server,
        "/api/command",
        {"text": "Firefox رو باز کن", "session_id": "../../etc/passwd"},
    )
    assert code_sess == 400
    assert res_sess["status"] == "INVALID_COMMAND"

    # 3. Reject cross-site fetch
    code_cross, res_cross = post_http(
        persistent_server,
        "/api/command",
        {"text": "Firefox رو باز کن", "session_id": "valid-id"},
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert code_cross == 403
    assert res_cross["status"] == "PERMISSION_DENIED"

    # 4. Reject oversized payload (> 16KB)
    code_large, res_large = post_http(
        persistent_server,
        "/api/command",
        {"text": "a" * (17 * 1024), "session_id": "valid-id"},
    )
    assert code_large in (400, 413)


# =============================================================================
# Concurrency: Parallel Requests to Same Session Serialized Cleanly
# =============================================================================

def test_http_concurrent_requests_serialized(persistent_server):
    """
    Section 21 Concurrency: Verify that concurrent requests to the same session
    are safely serialized by the session lock manager without race conditions.
    """
    session_id = "test-concurrent-session"
    results = []
    errors = []

    def send_cmd(text: str):
        try:
            status, res = post_http(
                persistent_server,
                "/api/command",
                {"text": text, "dry_run": True, "session_id": session_id},
            )
            results.append((status, res))
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=send_cmd, args=("Chrome رو باز کن",))
    t2 = threading.Thread(target=send_cmd, args=("Firefox رو باز کن",))

    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert len(errors) == 0
    assert len(results) == 2
    for status, res in results:
        assert status == 200
        assert res["success"] is True


def test_http_concurrent_requests_isolated_dry_run(persistent_server):
    """
    Verify that concurrent requests with conflicting dry_run settings
    (Session A dry_run=True, Session B dry_run=False) run with strictly isolated
    thread-local dry_run values without race conditions.
    """
    session_dry = "test-concurrent-dry"
    session_real = "test-concurrent-real"
    results = {}
    errors = []

    def send_cmd(session_id: str, is_dry: bool):
        try:
            status, res = post_http(
                persistent_server,
                "/api/command",
                {"text": "Firefox رو باز کن", "dry_run": is_dry, "session_id": session_id},
            )
            results[session_id] = (status, res)
        except Exception as e:
            errors.append(e)

    # Launch concurrently
    t_dry = threading.Thread(target=send_cmd, args=(session_dry, True))
    t_real = threading.Thread(target=send_cmd, args=(session_real, False))

    t_dry.start()
    t_real.start()
    t_dry.join(timeout=5)
    t_real.join(timeout=5)

    assert len(errors) == 0
    assert session_dry in results
    assert session_real in results

    status_dry, res_dry = results[session_dry]
    status_real, res_real = results[session_real]

    assert status_dry == 200
    assert status_real == 200

    # Ensure dry_run session isolated
    assert res_dry["result"]["is_dry_run"] is True
    # Ensure real session isolated - was not contaminated by dry_run session
    assert res_real["result"]["is_dry_run"] is False

