"""
System intents executor for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
Security Hardening: Honest execution reporting and robust exception handling.
"""

import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import get_config
from app.core.constants import (
    INTENT_EXIT_APPLICATION,
    INTENT_OPEN_FILE_MANAGER,
    INTENT_OPEN_SETTINGS,
    INTENT_OPEN_TERMINAL,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_TAKE_SCREENSHOT,
)
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.executor.result import (
    STATUS_EXECUTION_ERROR,
    STATUS_FAILED,
    STATUS_NOT_SUPPORTED,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    ExecutionResult,
)

logger = get_logger("riata.executor.system")


def execute_open_terminal(intent: Intent) -> ExecutionResult:
    """Safely open system terminal."""
    config = get_config()
    terminal_candidates = [
        "x-terminal-emulator",
        "gnome-terminal",
        "ptyxis",
        "konsole",
        "xfce4-terminal",
        "alacritty",
        "kitty",
        "foot",
    ]

    selected: Optional[str] = None
    for term in terminal_candidates:
        if shutil.which(term):
            selected = term
            break

    if not selected:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_OPEN_TERMINAL,
            message_key="terminal_failed",
            params={},
            error="No terminal emulator binary found",
        )

    if config.dry_run:
        logger.info("Executing terminal: %s [DRY RUN — NOT EXECUTED]", selected)
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_TERMINAL,
            message_key="terminal_opened",
            params={},
            is_dry_run=True,
            action_summary=f"{selected} [DRY RUN]",
        )

    try:
        logger.info("Launching terminal: %s", selected)
        subprocess.Popen(
            [selected],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_TERMINAL,
            message_key="terminal_opened",
            params={},
            action_summary=f"Launched {selected}",
        )
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.error("Failed to launch terminal %s: %s", selected, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_OPEN_TERMINAL,
            message_key="terminal_failed",
            params={},
            error=str(e),
        )


def execute_open_file_manager(intent: Intent) -> ExecutionResult:
    """Safely open system file manager."""
    config = get_config()
    home = Path.home().resolve()

    fm_candidates = ["nautilus", "nemo", "thunar", "dolphin", "pcmanfm"]
    selected: Optional[str] = None
    for fm in fm_candidates:
        if shutil.which(fm):
            selected = fm
            break

    if not selected:
        if shutil.which("xdg-open"):
            selected = "xdg-open"

    if not selected:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_OPEN_FILE_MANAGER,
            message_key="file_manager_failed",
            params={},
            error="No file manager available",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_FILE_MANAGER,
            message_key="file_manager_opened",
            params={},
            is_dry_run=True,
            action_summary=f"{selected} {home} [DRY RUN]",
        )

    try:
        cmd = [selected]
        if selected == "xdg-open":
            cmd.append(str(home))
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_FILE_MANAGER,
            message_key="file_manager_opened",
            params={},
            action_summary=f"Launched {selected}",
        )
    except (PermissionError, FileNotFoundError, OSError) as e:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_OPEN_FILE_MANAGER,
            message_key="file_manager_failed",
            params={},
            error=str(e),
        )


def execute_open_settings(intent: Intent) -> ExecutionResult:
    """Safely open desktop settings panel."""
    config = get_config()
    settings_candidates = [
        "gnome-control-center",
        "systemsettings5",
        "systemsettings",
        "xfce4-settings-manager",
        "lxqt-config",
    ]

    selected: Optional[str] = None
    for s in settings_candidates:
        if shutil.which(s):
            selected = s
            break

    if not selected:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_OPEN_SETTINGS,
            message_key="settings_failed",
            params={},
            error="Settings utility not found",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_SETTINGS,
            message_key="settings_opened",
            params={},
            is_dry_run=True,
            action_summary=f"{selected} [DRY RUN]",
        )

    try:
        subprocess.Popen(
            [selected],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_SETTINGS,
            message_key="settings_opened",
            params={},
            action_summary=f"Launched {selected}",
        )
    except (PermissionError, FileNotFoundError, OSError) as e:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_OPEN_SETTINGS,
            message_key="settings_failed",
            params={},
            error=str(e),
        )


def execute_show_system_info(intent: Intent) -> ExecutionResult:
    """Safely gather non-sensitive system specs without root privileges."""
    os_name = "Linux"
    if Path("/etc/os-release").is_file():
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        os_name = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
    elif platform.system():
        os_name = f"{platform.system()} {platform.release()}"

    kernel = platform.release()
    hostname = socket.gethostname()
    cpu = platform.processor() or "x86_64"

    if Path("/proc/cpuinfo").is_file():
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        cpu = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    ram = "N/A"
    if Path("/proc/meminfo").is_file():
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        gb = round(kb / (1024 * 1024), 1)
                        ram = f"{gb} GB"
                        break
        except Exception:
            pass

    return ExecutionResult(
        success=True,
        executed=False,  # Information query, not a process execution
        status=STATUS_SUCCESS,
        intent_name=INTENT_SHOW_SYSTEM_INFO,
        message_key="system_info_body",
        params={
            "os": os_name,
            "kernel": kernel,
            "cpu": cpu,
            "ram": ram,
            "hostname": hostname,
        },
        action_summary="Retrieved system information",
    )


def execute_take_screenshot(intent: Intent) -> ExecutionResult:
    """Safely capture desktop screenshot."""
    config = get_config()
    shots_dir = Path.home() / "Pictures"
    if not shots_dir.exists():
        try:
            shots_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            shots_dir = Path.home()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    target_file = shots_dir / f"Screenshot_{timestamp}.png"

    screenshot_tools = [
        ("gnome-screenshot", ["-f", str(target_file)]),
        ("spectacle", ["-b", "-o", str(target_file)]),
        ("scrot", [str(target_file)]),
        ("import", ["-window", "root", str(target_file)]),
    ]

    chosen_tool = None
    chosen_args = []
    for tool, args in screenshot_tools:
        if shutil.which(tool):
            chosen_tool = tool
            chosen_args = args
            break

    if not chosen_tool:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_TAKE_SCREENSHOT,
            message_key="screenshot_failed",
            params={},
            error="No screenshot tool detected (e.g. gnome-screenshot, spectacle, scrot)",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_TAKE_SCREENSHOT,
            message_key="screenshot_saved",
            params={"path": str(target_file)},
            is_dry_run=True,
            action_summary=f"{chosen_tool} {' '.join(chosen_args)} [DRY RUN]",
        )

    try:
        subprocess.run(
            [chosen_tool] + chosen_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=5,
        )
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_TAKE_SCREENSHOT,
            message_key="screenshot_saved",
            params={"path": str(target_file)},
            action_summary=f"Saved screenshot to {target_file}",
        )
    except subprocess.TimeoutExpired as e:
        logger.error("Screenshot utility timed out: %s", e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_TIMEOUT,
            intent_name=INTENT_TAKE_SCREENSHOT,
            message_key="screenshot_failed",
            params={},
            error="Screenshot command timed out",
        )
    except (subprocess.CalledProcessError, PermissionError, FileNotFoundError, OSError) as e:
        logger.error("Screenshot command failed: %s", e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_TAKE_SCREENSHOT,
            message_key="screenshot_failed",
            params={},
            error=str(e),
        )


def execute_exit_application(intent: Intent) -> ExecutionResult:
    """Exit R.I.A.T.A application."""
    return ExecutionResult(
        success=True,
        executed=False,
        status=STATUS_SUCCESS,
        intent_name=INTENT_EXIT_APPLICATION,
        message_key="exit",
        params={},
        action_summary="Exiting R.I.A.T.A",
    )
