"""
Files and folder executor for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import get_config
from app.core.constants import INTENT_OPEN_FILE, INTENT_OPEN_FOLDER
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.executor.result import ExecutionResult

logger = get_logger("riata.executor.files")


def resolve_folder_path(folder_name: str) -> Optional[Path]:
    """Safely resolve folder name to user directory."""
    home = Path.home().resolve()
    name_lower = folder_name.lower().strip()

    mapping = {
        "home": home,
        "downloads": home / "Downloads",
        "documents": home / "Documents",
        "pictures": home / "Pictures",
        "music": home / "Music",
        "videos": home / "Videos",
        "desktop": home / "Desktop",
    }

    if name_lower in mapping:
        path = mapping[name_lower]
        # Auto-create if standard user dir doesn't exist
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        return path

    # Check direct subdirectory in home
    sub = home / folder_name
    try:
        resolved = sub.resolve()
        # Enforce filesystem safety: must be within user home
        if str(resolved).startswith(str(home)) and resolved.is_dir():
            return resolved
    except Exception:
        pass

    return None


def execute_open_folder(intent: Intent) -> ExecutionResult:
    """Safely open local folder."""
    config = get_config()
    folder_name = intent.entities.get("folder")
    if not folder_name:
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="clarify_folder",
            params={},
        )

    folder_path = resolve_folder_path(folder_name)
    if not folder_path or not folder_path.is_dir():
        logger.warning("Folder not found or invalid: %s", folder_name)
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
        )

    logger.info("Opening folder: %s", folder_path)

    if config.dry_run:
        logger.info("Execution successful [DRY RUN — NOT EXECUTED]")
        return ExecutionResult(
            success=True,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_opened",
            params={"folder_name": folder_name},
            is_dry_run=True,
            action_summary=f"xdg-open {folder_path} [DRY RUN]",
        )

    xdg_open = shutil.which("xdg-open")
    if not xdg_open:
        # Fallback to file manager
        xdg_open = shutil.which("nautilus") or shutil.which("gio")

    if not xdg_open:
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error="xdg-open not available",
        )

    try:
        subprocess.Popen(
            [xdg_open, str(folder_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("Folder opened successfully: %s", folder_path)
        return ExecutionResult(
            success=True,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_opened",
            params={"folder_name": folder_name},
            action_summary=f"Opened {folder_path}",
        )
    except Exception as e:
        logger.error("Failed to open folder %s: %s", folder_path, e)
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error=str(e),
        )


def execute_open_file(intent: Intent) -> ExecutionResult:
    """Safely open a local file with system default handler."""
    config = get_config()
    file_target = intent.entities.get("file")
    if not file_target:
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={},
        )

    path = Path(file_target).expanduser().resolve()
    # Safety check: do not open sensitive system files like /etc/shadow
    home = Path.home().resolve()
    if not str(path).startswith(str(home)) and not str(path).startswith("/tmp"):
        logger.warning("Disallowed file path outside user home: %s", path)
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={},
            error="Path outside user space",
        )

    if not path.is_file():
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={"file_name": path.name},
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_opened",
            params={"file_name": path.name},
            is_dry_run=True,
            action_summary=f"xdg-open {path} [DRY RUN]",
        )

    xdg_open = shutil.which("xdg-open")
    if not xdg_open:
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={"file_name": path.name},
            error="xdg-open not available",
        )

    try:
        subprocess.Popen(
            [xdg_open, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ExecutionResult(
            success=True,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_opened",
            params={"file_name": path.name},
            action_summary=f"Opened {path}",
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={"file_name": path.name},
            error=str(e),
        )
