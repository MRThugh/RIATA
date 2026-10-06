"""
Application executor for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
Security Hardening: Honest execution reporting, strict allowlist enforcement, and zero shell invocation.
"""

import subprocess
from typing import Optional

from app.core.config import get_config
from app.core.constants import INTENT_OPEN_APPLICATION
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.executor.result import (
    STATUS_APP_NOT_FOUND,
    STATUS_EXECUTION_ERROR,
    STATUS_INVALID_COMMAND,
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

    # 3. Check if installed on current Ubuntu system
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

    # 4. Safe execution without shell=True
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
