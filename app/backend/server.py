"""
Persistent HTTP Backend Server for R.I.A.T.A v0.2.0 Web Companion
Author: Ali Kamrani (MRThugh)

Provides a persistent, thread-safe, local-only HTTP API interface to the
deterministic IntentRouter, ContextManager, and Execution Engine.

Ensures in-memory lifecycle persistence across requests for:
- Pending security confirmation tokens
- Multi-step execution plans
- Active application and directory context
- Pronoun resolution targets
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import urlparse

from app.core.config import get_config, thread_dry_run
from app.core.constants import APP_NAME, __version__
from app.core.logger import LOG_BUFFER, get_logger
from app.engine.router import IntentRouter, get_intent_router

logger = get_logger("riata.backend.server")

# Security constants
LOOPBACK_HOSTNAMES = frozenset({"127.0.0.1", "localhost", "::1"})
LOOPBACK_IPS = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ALLOWED_CLIENT_IDENTIFIERS = frozenset({"web-v0.2.0"})
MAX_PAYLOAD_SIZE = 16 * 1024  # 16 KB
MAX_COMMAND_LENGTH = 500


def parse_hostname(raw_host: str) -> Optional[str]:
    """Extract and normalize host part, handling ports and IPv6 brackets safely."""
    if not raw_host:
        return None
    try:
        # Standardize by prepending scheme for URL parsing
        parsed = urlparse(f"http://{raw_host}")
        host = parsed.hostname
        if host and host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
        return host.lower() if host else None
    except Exception:
        return None


def is_allowed_loopback_host(hostname: Optional[str]) -> bool:
    """Return True if hostname is strictly local loopback."""
    if not hostname:
        return False
    return hostname in LOOPBACK_HOSTNAMES


class SessionLockManager:
    """Provides thread-safe, per-session synchronization to prevent concurrency races."""

    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def get_lock(self, session_id: str) -> threading.Lock:
        with self._guard:
            if session_id not in self._locks:
                self._locks[session_id] = threading.Lock()
            return self._locks[session_id]

    def remove_lock(self, session_id: str) -> None:
        with self._guard:
            self._locks.pop(session_id, None)


_SESSION_LOCKS = SessionLockManager()


class RiataBackendHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler for R.I.A.T.A Persistent Backend.
    Enforces loopback isolation, origin validation, payload bounds, and structured responses.
    """

    server_version = f"RIATA/{__version__}"

    def log_message(self, format: str, *args: Any) -> None:
        # Route through R.I.A.T.A structured logging instead of raw stderr
        logger.debug(f"%s - - [{self.log_date_time_string()}] {format % args}")

    def _send_json_response(
        self,
        status_code: int,
        data: dict[str, Any],
        origin: Optional[str] = None,
    ) -> None:
        """Serialize and send structured JSON response with security headers."""
        try:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-RIATA-Client")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            logger.debug("Client disconnected before response could be sent.")

    def _validate_request_security(self, is_options: bool = False) -> tuple[bool, int, str, Optional[str]]:
        """
        Comprehensive security verification:
        1. Remote client IP is strictly loopback (rejects LAN, 0.0.0.0, Wi-Fi).
        2. Sec-Fetch-Site is not cross-site.
        3. Host header is strictly loopback.
        4. Origin header (if present) is strictly loopback.
        5. X-RIATA-Client matches expected identifier.
        """
        # 1. Loopback IP restriction
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in LOOPBACK_IPS:
            return (
                False,
                HTTPStatus.FORBIDDEN,
                f"Forbidden: Access rejected from non-loopback address ({client_ip}).",
                None,
            )

        # 2. Cross-site isolation
        sec_fetch_site = self.headers.get("Sec-Fetch-Site", "").lower()
        if sec_fetch_site == "cross-site":
            return (
                False,
                HTTPStatus.FORBIDDEN,
                "Forbidden: Cross-site request rejected.",
                None,
            )

        # 3. Host header validation
        host_header = self.headers.get("Host", "")
        host_name = parse_hostname(host_header)
        if not is_allowed_loopback_host(host_name):
            return (
                False,
                HTTPStatus.FORBIDDEN,
                "Forbidden: Host header must be local loopback.",
                None,
            )

        # 4. Origin header validation
        origin_header = self.headers.get("Origin")
        matched_origin: Optional[str] = None
        if origin_header:
            origin_name = parse_hostname(origin_header)
            if not is_allowed_loopback_host(origin_name):
                return (
                    False,
                    HTTPStatus.FORBIDDEN,
                    f"Forbidden: Origin '{origin_header}' is unauthorized.",
                    None,
                )
            matched_origin = origin_header

        # Preflight OPTIONS permits preflight without X-RIATA-Client
        if is_options:
            return (True, HTTPStatus.OK, "Authorized Preflight", matched_origin)

        # 5. Client identification header (identifier, not authentication)
        client_id = self.headers.get("X-RIATA-Client", "")
        if client_id not in ALLOWED_CLIENT_IDENTIFIERS:
            return (
                False,
                HTTPStatus.FORBIDDEN,
                "Forbidden: Missing or invalid 'X-RIATA-Client' identifier header.",
                None,
            )

        return (True, HTTPStatus.OK, "Authorized", matched_origin)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests securely."""
        allowed, status_code, message, origin = self._validate_request_security(is_options=True)
        if not allowed:
            self._send_json_response(status_code, {"error": message, "status": "PERMISSION_DENIED"})
            return

        self.send_response(HTTPStatus.NO_CONTENT)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-RIATA-Client")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle health-check probes."""
        parsed_path = urlparse(self.path).path
        if parsed_path in ("/health", "/api/health"):
            self._send_json_response(
                HTTPStatus.OK,
                {"status": "ok", "app": APP_NAME, "version": __version__},
                origin=self.headers.get("Origin"),
            )
            return

        self._send_json_response(
            HTTPStatus.NOT_FOUND,
            {"error": "Endpoint not found", "status": "NOT_FOUND"},
            origin=self.headers.get("Origin"),
        )

    def do_POST(self) -> None:
        """Handle API command, reset-context, and run-tests requests."""
        content_length_str = self.headers.get("Content-Length")
        try:
            content_length = int(content_length_str) if content_length_str else 0
        except ValueError:
            content_length = 0

        allowed, status_code, message, origin = self._validate_request_security()
        if not allowed:
            if 0 < content_length <= MAX_PAYLOAD_SIZE:
                try:
                    self.rfile.read(content_length)
                except Exception:
                    pass
            self._send_json_response(
                status_code,
                {"success": False, "status": "PERMISSION_DENIED", "message": message, "executed": False},
                origin=origin,
            )
            return

        # Read and bound body payload
        content_length_str = self.headers.get("Content-Length")
        try:
            content_length = int(content_length_str) if content_length_str else 0
        except ValueError:
            self._send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "status": "INVALID_COMMAND", "message": "Invalid Content-Length."},
                origin=origin,
            )
            return

        if content_length > MAX_PAYLOAD_SIZE:
            try:
                self.rfile.read(min(content_length, 64 * 1024))
            except Exception:
                pass
            self.close_connection = True
            self._send_json_response(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"success": False, "status": "INVALID_COMMAND", "message": "Payload Too Large. Maximum allowed is 16KB."},
                origin=origin,
            )
            return

        try:
            raw_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            payload = json.loads(raw_body or "{}")
        except Exception:
            self._send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "status": "INVALID_COMMAND", "message": "Malformed JSON payload."},
                origin=origin,
            )
            return

        parsed_path = urlparse(self.path).path

        if parsed_path == "/api/command":
            self._handle_command(payload, origin)
        elif parsed_path == "/api/reset-context":
            self._handle_reset_context(payload, origin)
        elif parsed_path == "/api/run-tests":
            self._handle_run_tests(origin)
        else:
            self._send_json_response(
                HTTPStatus.NOT_FOUND,
                {"success": False, "status": "NOT_FOUND", "message": f"Endpoint '{parsed_path}' not found."},
                origin=origin,
            )

    def _handle_command(self, payload: dict[str, Any], origin: Optional[str]) -> None:
        """Execute command through persistent IntentRouter and ContextManager."""
        command_text = payload.get("text")
        dry_run = bool(payload.get("dry_run", False))
        session_id = payload.get("session_id", "web-companion")

        # Validation
        if not isinstance(command_text, str) or not command_text.strip():
            self._send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "status": "INVALID_COMMAND", "message": "Field 'text' must be a non-empty string."},
                origin=origin,
            )
            return

        if len(command_text) > MAX_COMMAND_LENGTH:
            self._send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "status": "INVALID_COMMAND", "message": f"Command exceeds maximum length of {MAX_COMMAND_LENGTH} characters."},
                origin=origin,
            )
            return

        if not isinstance(session_id, str) or not SESSION_ID_PATTERN.match(session_id):
            self._send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "status": "INVALID_COMMAND", "message": "Invalid session_id format. Must match ^[A-Za-z0-9_-]{1,64}$."},
                origin=origin,
            )
            return

        # Acquire per-session lock to serialize concurrent requests to the same session
        session_lock = _SESSION_LOCKS.get_lock(session_id)
        with session_lock:
            try:
                with thread_dry_run(dry_run):
                    router: IntentRouter = get_intent_router()
                    output = router.process(command_text, session_id=session_id)

                result_dict = output.result.to_dict() if output.result else {
                    "success": False,
                    "executed": False,
                    "status": "UNKNOWN",
                    "message": output.response_text,
                }

                session_ctx = router.context_manager.get_session(session_id)
                # In-memory dictionary representation includes pending_confirmation for UI rendering
                ctx_dict = session_ctx.to_dict(include_pending_confirmation=True) if session_ctx else {}

                response_data = {
                    "success": output.result.success if output.result else False,
                    "executed": output.result.executed if output.result else False,
                    "status": output.result.status if output.result else "SUCCESS",
                    "response": output.response_text,
                    "intent": output.intent.to_dict() if output.intent else None,
                    "result": result_dict,
                    "direction": output.direction,
                    "is_exit": output.is_exit,
                    "plan": output.plan.to_dict() if output.plan else None,
                    "context": ctx_dict,
                    "session_id": session_id,
                    "logs": list(LOG_BUFFER)[-15:],
                }

                self._send_json_response(HTTPStatus.OK, response_data, origin=origin)
            except Exception as e:
                logger.error("Exception during intent command processing: %s", e, exc_info=True)
                # Never expose raw stack traces to client
                self._send_json_response(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "success": False,
                        "executed": False,
                        "status": "EXECUTION_ERROR",
                        "message": "Internal error occurred while processing command.",
                    },
                    origin=origin,
                )

    def _handle_reset_context(self, payload: dict[str, Any], origin: Optional[str]) -> None:
        """Reset contextual state and pending confirmations for a specific session."""
        session_id = payload.get("session_id", "web-companion")
        if not isinstance(session_id, str) or not SESSION_ID_PATTERN.match(session_id):
            self._send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"success": False, "status": "INVALID_COMMAND", "message": "Invalid session_id format. Must match ^[A-Za-z0-9_-]{1,64}$."},
                origin=origin,
            )
            return

        session_lock = _SESSION_LOCKS.get_lock(session_id)
        with session_lock:
            try:
                router = get_intent_router()
                session_ctx = router.context_manager.get_session(session_id)
                if session_ctx:
                    session_ctx.clear()
                router.context_manager.reset(session_id)
                router.reset_context()

                self._send_json_response(
                    HTTPStatus.OK,
                    {
                        "success": True,
                        "status": "SUCCESS",
                        "message": "Context reset successfully",
                        "session_id": session_id,
                    },
                    origin=origin,
                )
            except Exception as e:
                logger.error("Exception during context reset: %s", e)
                self._send_json_response(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"success": False, "status": "FAILED", "message": "Failed to reset session context."},
                    origin=origin,
                )

    def _handle_run_tests(self, origin: Optional[str]) -> None:
        """Execute automated test suite when explicitly enabled in development."""
        if os.environ.get("RIATA_ENABLE_TEST_API") != "true":
            self._send_json_response(
                HTTPStatus.FORBIDDEN,
                {
                    "error": "Test execution API is disabled in production (set RIATA_ENABLE_TEST_API=true to enable).",
                    "status": "FORBIDDEN",
                },
                origin=origin,
            )
            return

        try:
            proc = subprocess.run(
                ["pytest", "-v"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = proc.stdout + proc.stderr
            max_len = 256 * 1024
            truncated = False
            if len(output) > max_len:
                output = output[:max_len] + "\n[Output truncated at 256KB limit]"
                truncated = True

            self._send_json_response(
                HTTPStatus.OK,
                {
                    "output": output,
                    "passed": proc.returncode == 0,
                    "status": "SUCCESS" if proc.returncode == 0 else "FAILED",
                    "truncated": truncated,
                },
                origin=origin,
            )
        except subprocess.TimeoutExpired:
            self._send_json_response(
                HTTPStatus.GATEWAY_TIMEOUT,
                {"output": "Test execution timed out after 60 seconds.", "passed": False, "status": "TIMEOUT"},
                origin=origin,
            )
        except Exception as e:
            self._send_json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Failed to execute tests: {e}", "passed": False, "status": "FAILED"},
                origin=origin,
            )


def create_server(host: str = "127.0.0.1", port: int = 5005) -> ThreadingHTTPServer:
    """Instantiate ThreadingHTTPServer bound strictly to local loopback."""
    if not is_allowed_loopback_host(host):
        raise ValueError(f"Security violation: RIATA Backend can only bind to loopback, not '{host}'.")
    server = ThreadingHTTPServer((host, port), RiataBackendHandler)
    server.daemon_threads = True
    return server


def run_server(host: str = "127.0.0.1", port: int = 5005) -> None:
    """Run persistent HTTP backend server until interrupted."""
    server = create_server(host=host, port=port)
    logger.info("R.I.A.T.A v%s Persistent Backend listening on http://%s:%d", __version__, host, port)
    print(f"R.I.A.T.A v{__version__} Persistent Backend started on http://{host}:{port}")
    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down R.I.A.T.A Backend Server...")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{__version__} Backend Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (must be loopback, default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5005, help="Port to listen on (default: 5005)")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
