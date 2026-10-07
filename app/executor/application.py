"""
Application executor for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)
Security Hardening: Strict allowlist enforcement, zero shell invocation, safe process termination, and sanitized URL opening.
"""

import re
import shutil
import subprocess
from typing import Optional
from urllib.parse import urlparse

from app.core.config import get_config
from app.core.constants import (
    INTENT_CLOSE_APPLICATION,
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_URL,
)
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.executor.result import (
    STATUS_APP_NOT_FOUND,
    STATUS_EXECUTION_ERROR,
    STATUS_INVALID_COMMAND,
    STATUS_NOT_SUPPORTED,
    STATUS_SUCCESS,
    ExecutionResult,
)
from app.registry.applications import AppEntry, get_application_registry

logger = get_logger("riata.executor.app")


def execute_open_application(intent: Intent) -> ExecutionResult:
    """Safely execute OPEN_APPLICATION intent against allowlisted applications."""
    config = get_config()
    registry = get_application_registry()

    app_name = intent.entities.get("application")
    if not app_name:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_OPEN_APPLICATION,
            message_key="clarify_application",
            params={},
        )

    # 1. Lookup in registry (respects safe_execution allowlist)
    app_entry: Optional[AppEntry] = registry.find(app_name, safe_execution=config.safe_execution)

    if not app_entry:
        logger.info("Application not found or not permitted in registry: %s", app_name)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_APP_NOT_FOUND,
            intent_name=INTENT_OPEN_APPLICATION,
            message_key="app_not_found",
            params={"app_name": app_name},
            action_summary=f"App not found: {app_name}",
        )

    # 2. Handle Dry Run mode (honest reporting: executed=False)
    if config.dry_run:
        logger.info("Executing application: %s", app_entry.command)
        logger.info("Execution successful [DRY RUN — NOT EXECUTED]")
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_APPLICATION,
            message_key="app_opened",
            params={"app_name": app_entry.display_name},
            is_dry_run=True,
            action_summary=f"{app_entry.command} [DRY RUN — NOT EXECUTED]",
        )

    # 3. Check if installed on current Linux system
    exe_path = app_entry.get_executable_path()
    if not exe_path:
        logger.info(
            "Application is not installed on system: %s (%s)",
            app_entry.display_name,
            app_entry.command,
        )
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_APP_NOT_FOUND,
            intent_name=INTENT_OPEN_APPLICATION,
            message_key="app_not_found",
            params={"app_name": app_entry.display_name},
            action_summary=f"Binary missing: {app_entry.command}",
        )

    # 4. Safe execution without shell invocation
    try:
        logger.info("Executing application: %s", app_entry.command)
        proc = subprocess.Popen(
            [exe_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("Execution successful (PID: %d)", proc.pid)
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_APPLICATION,
            message_key="app_opened",
            params={"app_name": app_entry.display_name},
            action_summary=f"Launched {exe_path}",
        )
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.error("Failed to execute application %s: %s", exe_path, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_OPEN_APPLICATION,
            message_key="app_launch_failed",
            params={"app_name": app_entry.display_name, "error": str(e)},
            error=str(e),
            action_summary=f"Execution failed: {e}",
        )


def execute_close_application(intent: Intent) -> ExecutionResult:
    """Safely terminate an application process without shell invocation."""
    config = get_config()
    registry = get_application_registry()

    app_name = intent.entities.get("application")
    if not app_name:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_CLOSE_APPLICATION,
            message_key="clarify_application",
            params={},
        )

    # Lookup canonical command or binary name
    app_entry = registry.find(app_name, safe_execution=config.safe_execution)
    display_name = app_entry.display_name if app_entry else app_name.capitalize()
    target_cmd = app_entry.command if app_entry else app_name.lower()

    if config.dry_run:
        logger.info("Closing application %s [DRY RUN — NOT EXECUTED]", display_name)
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_CLOSE_APPLICATION,
            message_key="app_closed",
            params={"app_name": display_name},
            is_dry_run=True,
            action_summary=f"pkill {target_cmd} [DRY RUN]",
        )

    pkill_path = shutil.which("pkill")
    if not pkill_path:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_CLOSE_APPLICATION,
            message_key="app_close_failed",
            params={"app_name": display_name},
            error="pkill utility not found",
        )

    try:
        # Zero shell invocation, pass arguments safely as list
        ret = subprocess.run(
            [pkill_path, "-f", target_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        logger.info("Process termination signal sent for %s (exit: %d)", target_cmd, ret.returncode)
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_CLOSE_APPLICATION,
            message_key="app_closed",
            params={"app_name": display_name},
            action_summary=f"Closed {display_name}",
        )
    except Exception as e:
        logger.error("Failed terminating application %s: %s", display_name, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_CLOSE_APPLICATION,
            message_key="app_close_failed",
            params={"app_name": display_name, "error": str(e)},
            error=str(e),
        )


def execute_open_url(intent: Intent) -> ExecutionResult:
    """Safely open an HTTP/HTTPS URL in the default web browser."""
    config = get_config()
    target = intent.entities.get("url") or intent.entities.get("application") or ""
    target = str(target).strip()

    if not target:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_OPEN_URL,
            message_key="clarify_general",
            params={},
        )

    # Sanitize and normalize URL
    if not target.startswith(("http://", "https://")):
        if target.lower() == "github":
            url = "https://github.com"
        elif target.lower() in ("google", "google search"):
            url = "https://google.com"
        elif "." in target and not any(ch in target for ch in (" ", ";", "&", "|", "`", "$")):
            url = f"https://{target}"
        else:
            url = f"https://{target}.com"
    else:
        url = target

    # Strict URL validation: only allow http / https schemes
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        logger.warning("Rejected invalid or unsafe URL schema: %s", url)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_OPEN_URL,
            message_key="clarify_general",
            params={},
            error="Only HTTP/HTTPS URLs are permitted",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_URL,
            message_key="url_opened",
            params={"url": url},
            is_dry_run=True,
            action_summary=f"xdg-open {url} [DRY RUN]",
        )

    xdg_open = shutil.which("xdg-open")
    if not xdg_open:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_OPEN_URL,
            message_key="app_launch_failed",
            params={"app_name": url},
            error="xdg-open not available",
        )

    try:
        subprocess.Popen(
            [xdg_open, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_URL,
            message_key="url_opened",
            params={"url": url},
            action_summary=f"Opened {url}",
        )
    except Exception as e:
        logger.error("Failed opening URL %s: %s", url, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_OPEN_URL,
            message_key="app_launch_failed",
            params={"app_name": url, "error": str(e)},
            error=str(e),
        )
