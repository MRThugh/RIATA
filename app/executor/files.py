"""
Files and folder executor for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
Security Hardening: Strict filesystem sandbox containment and symlink escape prevention.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from app.core.config import get_config
from app.core.constants import (
    INTENT_CREATE_FILE,
    INTENT_CREATE_FOLDER,
    INTENT_DELETE_FILE,
    INTENT_DELETE_FOLDER,
    INTENT_OPEN_FILE,
    INTENT_OPEN_FOLDER,
)
from app.core.logger import get_logger
from app.engine.intent import Intent
from app.executor.result import (
    STATUS_EXECUTION_ERROR,
    STATUS_FAILED,
    STATUS_INVALID_COMMAND,
    STATUS_NOT_SUPPORTED,
    STATUS_PATH_NOT_ALLOWED,
    STATUS_SUCCESS,
    ExecutionResult,
)

logger = get_logger("riata.executor.files")

# Sensitive hidden folders and credential stores within user home that must never be opened
SENSITIVE_HOME_PARTS = {
    ".ssh",
    ".gnupg",
    ".pki",
    ".aws",
    ".docker",
    ".kube",
    ".password-store",
    ".netrc",
    ".bash_history",
    ".zsh_history",
}


def is_allowed_path(
    path: Path | str,
    base_dir: Optional[Path] = None,
    allow_tmp: bool = True,
) -> bool:
    """
    Validate that target path resolves strictly inside user home (or /tmp).

    Security Properties:
    - Resolves all symlinks (preventing symlink escape attacks to /etc, etc.)
    - Eliminates '..' and '.' traversal attempts
    - Uses pathlib.Path containment logic (relative_to), preventing prefix bypasses
      such as '/home/user2' matching '/home/user'
    - Prevents traversal into sensitive credentials directories (.ssh, .gnupg)
    """
    if not path:
        return False

    try:
        raw = Path(path).expanduser()
        # Resolve symlinks and relative components
        target = raw.resolve(strict=False)
        home = (base_dir or Path.home()).resolve()

        # 1. Check user home directory containment
        try:
            rel = target.relative_to(home)
            # Ensure not inside sensitive credential folders
            for part in rel.parts:
                if part in SENSITIVE_HOME_PARTS:
                    logger.warning("Attempted access to protected directory: %s", part)
                    return False
            return True
        except ValueError:
            pass

        # 2. Check /tmp containment if permitted
        if allow_tmp:
            tmp = Path("/tmp").resolve()
            try:
                target.relative_to(tmp)
                return True
            except ValueError:
                pass

        return False
    except Exception as e:
        logger.debug("Path validation failed with exception: %s", e)
        return False


def resolve_folder_path(folder_name: str, base_dir: Optional[Path] = None) -> Optional[Path]:
    """Safely resolve folder name to an allowed directory within user home."""
    if not folder_name:
        return None

    home = (base_dir or Path.home()).resolve()
    name_clean = folder_name.strip()
    name_lower = name_clean.lower()

    canonical_map = {
        "home": home,
        "downloads": home / "Downloads",
        "documents": home / "Documents",
        "pictures": home / "Pictures",
        "music": home / "Music",
        "videos": home / "Videos",
        "desktop": home / "Desktop",
    }

    if name_lower in canonical_map:
        path = canonical_map[name_lower]
        # Auto-create if standard user dir doesn't exist
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        return path

    # Check custom subdirectory inside home
    candidate = (home / name_clean).expanduser()
    try:
        resolved = candidate.resolve(strict=False)
        # Enforce strict filesystem containment check
        if is_allowed_path(resolved, base_dir=home, allow_tmp=False) and resolved.is_dir():
            return resolved
    except Exception as e:
        logger.debug("Failed resolving custom folder '%s': %s", folder_name, e)

    return None


def execute_open_folder(intent: Intent) -> ExecutionResult:
    """Safely open local folder using system handler."""
    config = get_config()
    folder_name = intent.entities.get("folder")
    if not folder_name:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="clarify_folder",
            params={},
        )

    folder_path = resolve_folder_path(folder_name)
    if not folder_path or not folder_path.is_dir():
        logger.warning("Folder not found or outside sandbox: %s", folder_name)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED if folder_path is None else STATUS_FAILED,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
        )

    logger.info("Opening folder: %s", folder_path)

    if config.dry_run:
        logger.info("Execution successful [DRY RUN — NOT EXECUTED]")
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_opened",
            params={"folder_name": folder_name},
            is_dry_run=True,
            action_summary=f"xdg-open {folder_path} [DRY RUN]",
        )

    xdg_open = shutil.which("xdg-open") or shutil.which("nautilus") or shutil.which("gio")
    if not xdg_open:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error="No folder handler available (xdg-open / nautilus missing)",
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
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_opened",
            params={"folder_name": folder_name},
            action_summary=f"Opened {folder_path}",
        )
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.error("Failed to open folder %s: %s", folder_path, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_OPEN_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error=str(e),
        )


def execute_open_file(intent: Intent) -> ExecutionResult:
    """Safely open a local file with system default handler within allowed sandbox."""
    config = get_config()
    file_target = intent.entities.get("file")
    if not file_target:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={},
        )

    raw_path = Path(file_target).expanduser()
    try:
        resolved = raw_path.resolve(strict=False)
    except Exception as e:
        logger.warning("Invalid path resolution for %s: %s", file_target, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={},
            error="Invalid path",
        )

    # Security check: strict sandbox containment check
    if not is_allowed_path(resolved, allow_tmp=True):
        logger.warning("Disallowed file path outside allowed user sandbox: %s", resolved)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={},
            error="Path outside allowed sandbox",
        )

    if not resolved.is_file():
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_FAILED,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={"file_name": resolved.name},
            error="File does not exist",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_opened",
            params={"file_name": resolved.name},
            is_dry_run=True,
            action_summary=f"xdg-open {resolved} [DRY RUN]",
        )

    xdg_open = shutil.which("xdg-open")
    if not xdg_open:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_NOT_SUPPORTED,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={"file_name": resolved.name},
            error="xdg-open not available",
        )

    try:
        subprocess.Popen(
            [xdg_open, str(resolved)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_opened",
            params={"file_name": resolved.name},
            action_summary=f"Opened {resolved}",
        )
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.error("Failed to open file %s: %s", resolved, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_OPEN_FILE,
            message_key="file_not_found",
            params={"file_name": resolved.name},
            error=str(e),
        )


def execute_create_file(intent: Intent) -> ExecutionResult:
    """Safely create an empty file strictly inside the allowed user sandbox."""
    config = get_config()
    file_name = intent.entities.get("file")
    folder_name = intent.entities.get("folder")

    if not file_name:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_CREATE_FILE,
            message_key="clarify_general",
            params={},
        )

    # Determine base directory
    base_dir = Path.home()
    if folder_name:
        resolved_folder = resolve_folder_path(folder_name)
        if resolved_folder and resolved_folder.is_dir():
            base_dir = resolved_folder

    target_candidate = (base_dir / file_name).expanduser()
    try:
        resolved_target = target_candidate.resolve(strict=False)
    except Exception as e:
        logger.warning("Failed resolving target creation file %s: %s", file_name, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_CREATE_FILE,
            message_key="file_not_found",
            params={"file_name": file_name},
            error="Invalid path",
        )

    # Security: strict containment check within user sandbox
    if not is_allowed_path(resolved_target, allow_tmp=True):
        logger.warning("File creation path rejected outside sandbox: %s", resolved_target)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_CREATE_FILE,
            message_key="file_not_found",
            params={"file_name": resolved_target.name},
            error="Target path outside allowed sandbox",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_CREATE_FILE,
            message_key="file_created",
            params={"file_name": resolved_target.name},
            is_dry_run=True,
            action_summary=f"touch {resolved_target} [DRY RUN]",
        )

    try:
        # Ensure parent directory exists
        resolved_target.parent.mkdir(parents=True, exist_ok=True)
        resolved_target.touch(exist_ok=True)
        logger.info("Successfully created file: %s", resolved_target)
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_CREATE_FILE,
            message_key="file_created",
            params={"file_name": resolved_target.name},
            action_summary=f"Created {resolved_target.name}",
        )
    except Exception as e:
        logger.error("Failed creating file %s: %s", resolved_target, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_CREATE_FILE,
            message_key="file_not_found",
            params={"file_name": resolved_target.name},
            error=str(e),
        )


def execute_delete_file(intent: Intent) -> ExecutionResult:
    """Safely delete a file strictly inside the allowed user sandbox."""
    config = get_config()
    file_name = intent.entities.get("file")
    if not file_name:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_DELETE_FILE,
            message_key="clarify_general",
            params={},
        )

    # Resolve target path relative to home or specified path
    folder_name = intent.entities.get("folder")
    base_dir = Path.home()
    if folder_name:
        resolved_folder = resolve_folder_path(folder_name)
        if resolved_folder and resolved_folder.is_dir():
            base_dir = resolved_folder

    target_candidate = Path(file_name).expanduser()
    if not target_candidate.is_absolute():
        target_candidate = base_dir / file_name

    try:
        resolved_target = target_candidate.resolve(strict=False)
    except Exception as e:
        logger.warning("Failed resolving deletion target %s: %s", file_name, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_DELETE_FILE,
            message_key="file_not_found",
            params={"file_name": file_name},
            error="Invalid path",
        )

    # Security check: strict sandbox containment
    if not is_allowed_path(resolved_target, allow_tmp=True):
        logger.warning("File deletion path rejected outside sandbox: %s", resolved_target)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_DELETE_FILE,
            message_key="file_not_found",
            params={"file_name": resolved_target.name},
            error="Target path outside allowed sandbox",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_DELETE_FILE,
            message_key="file_deleted",
            params={"file_name": resolved_target.name},
            is_dry_run=True,
            action_summary=f"rm {resolved_target} [DRY RUN]",
        )

    if not resolved_target.is_file():
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_FAILED,
            intent_name=INTENT_DELETE_FILE,
            message_key="file_not_found",
            params={"file_name": resolved_target.name},
            error="File does not exist",
        )

    try:
        resolved_target.unlink()
        logger.info("Successfully deleted file: %s", resolved_target)
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_DELETE_FILE,
            message_key="file_deleted",
            params={"file_name": resolved_target.name},
            action_summary=f"Deleted {resolved_target.name}",
        )
    except Exception as e:
        logger.error("Failed deleting file %s: %s", resolved_target, e)
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_DELETE_FILE,
            message_key="file_not_found",
            params={"file_name": resolved_target.name},
            error=str(e),
        )


def execute_create_folder(intent: Intent) -> ExecutionResult:
    """Safely create a directory inside user home."""
    config = get_config()
    folder_name = intent.entities.get("folder")
    if not folder_name:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_CREATE_FOLDER,
            message_key="clarify_folder",
            params={},
        )

    target_candidate = (Path.home() / folder_name).expanduser()
    try:
        resolved_target = target_candidate.resolve(strict=False)
    except Exception as e:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_CREATE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error=str(e),
        )

    if not is_allowed_path(resolved_target, allow_tmp=True):
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_CREATE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error="Target path outside allowed sandbox",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_CREATE_FOLDER,
            message_key="folder_opened",
            params={"folder_name": resolved_target.name},
            is_dry_run=True,
            action_summary=f"mkdir -p {resolved_target} [DRY RUN]",
        )

    try:
        resolved_target.mkdir(parents=True, exist_ok=True)
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_CREATE_FOLDER,
            message_key="folder_opened",
            params={"folder_name": resolved_target.name},
            action_summary=f"Created folder {resolved_target.name}",
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_CREATE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error=str(e),
        )


def execute_delete_folder(intent: Intent) -> ExecutionResult:
    """Safely delete an empty directory inside user home."""
    config = get_config()
    folder_name = intent.entities.get("folder")
    if not folder_name:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_INVALID_COMMAND,
            intent_name=INTENT_DELETE_FOLDER,
            message_key="clarify_folder",
            params={},
        )

    resolved_folder = resolve_folder_path(folder_name)
    if not resolved_folder or not resolved_folder.is_dir():
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_FAILED,
            intent_name=INTENT_DELETE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error="Directory does not exist",
        )

    if not is_allowed_path(resolved_folder, allow_tmp=True):
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_PATH_NOT_ALLOWED,
            intent_name=INTENT_DELETE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error="Path outside allowed sandbox",
        )

    if config.dry_run:
        return ExecutionResult(
            success=True,
            executed=False,
            status=STATUS_SUCCESS,
            intent_name=INTENT_DELETE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": resolved_folder.name},
            is_dry_run=True,
            action_summary=f"rmdir {resolved_folder} [DRY RUN]",
        )

    try:
        resolved_folder.rmdir()
        return ExecutionResult(
            success=True,
            executed=True,
            status=STATUS_SUCCESS,
            intent_name=INTENT_DELETE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": resolved_folder.name},
            action_summary=f"Deleted folder {resolved_folder.name}",
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            executed=False,
            status=STATUS_EXECUTION_ERROR,
            intent_name=INTENT_DELETE_FOLDER,
            message_key="folder_not_found",
            params={"folder_name": folder_name},
            error=str(e),
        )

