"""
Extensible application registry and system detector for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
Security Hardening: Strict allowlist enforcement, robust .desktop parsing, and rejection of dangerous binaries.
"""

import os
import re
import shlex
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.config import get_config
from app.core.constants import DANGEROUS_COMMANDS
from app.core.logger import get_logger

logger = get_logger("riata.registry")


@dataclass
class AppEntry:
    id: str
    display_name: str
    command: str
    aliases: list[str] = field(default_factory=list)
    desktop_file: Optional[str] = None
    icon: Optional[str] = None

    def is_installed(self) -> bool:
        """Check if command binary exists in system PATH or is an executable file."""
        return self.get_executable_path() is not None

    def get_executable_path(self) -> Optional[str]:
        """Return absolute path to executable binary if installed."""
        if os.path.isabs(self.command) and os.path.isfile(self.command) and os.access(self.command, os.X_OK):
            return self.command
        return shutil.which(self.command)


def parse_desktop_exec_line(raw_exec: str) -> Optional[str]:
    """
    Safely extract executable binary path/name from a Linux .desktop Exec line.

    Handles:
    - Quoted executable paths with spaces (e.g. "/opt/My App/bin/myapp" %u)
    - Command-line arguments
    - FreeDesktop field codes (%f, %F, %u, %U, %d, %D, %n, %N, %i, %c, %k, %v, %m, %%)
    - Env wrappers (e.g. env VAR=VAL app)
    - Malformed lines without crashing or invoking a shell
    """
    if not raw_exec or not raw_exec.strip():
        return None

    cleaned = raw_exec.strip()

    # Reject shell control operators anywhere in the raw line
    if any(ch in cleaned for ch in (";", "&", "|", "`", "$", ">", "<")):
        logger.warning("Rejected suspicious shell characters in desktop Exec: %s", cleaned)
        return None

    try:
        tokens = shlex.split(cleaned, posix=True)
    except Exception:
        # Fallback regex for unclosed quotes
        m = re.match(r'^"([^"]+)"', cleaned)
        if m:
            tokens = [m.group(1)]
        else:
            tokens = cleaned.split()

    if not tokens:
        return None

    # Step past 'env' or variable assignments if used as prefix
    idx = 0
    if tokens[idx] == "env":
        idx += 1
        while idx < len(tokens) and ("=" in tokens[idx] or tokens[idx].startswith("-")):
            idx += 1

    if idx >= len(tokens):
        return None

    exe = tokens[idx].strip()

    # Reject field codes
    if re.match(r"^%[a-zA-Z%]$", exe):
        return None

    # Reject shell control operators
    if any(ch in exe for ch in (";", "&", "|", "`", "$", ">", "<")):
        logger.warning("Rejected suspicious shell characters in desktop Exec: %s", exe)
        return None

    return exe


# Built-in canonical applications catalog with aliases in English and Persian
BUILTIN_APPS: list[AppEntry] = [
    AppEntry(
        id="firefox",
        display_name="Firefox",
        command="firefox",
        aliases=["firefox", "فایرفاکس", "مرورگر فایرفاکس", "mozilla firefox", "fire fox"],
    ),
    AppEntry(
        id="chrome",
        display_name="Google Chrome",
        command="google-chrome",
        aliases=["chrome", "google-chrome", "google chrome", "کروم", "گوگل کروم", "مرورگر کروم"],
    ),
    AppEntry(
        id="chromium",
        display_name="Chromium",
        command="chromium-browser",
        aliases=["chromium", "chromium-browser", "کرومیوم"],
    ),
    AppEntry(
        id="code",
        display_name="Visual Studio Code",
        command="code",
        aliases=["code", "vs code", "vscode", "visual studio code", "وی اس کد", "وی‌اس‌کد"],
    ),
    AppEntry(
        id="terminal",
        display_name="Terminal",
        command="x-terminal-emulator",
        aliases=["terminal", "x-terminal-emulator", "gnome-terminal", "ترمینال", "کنسول", "خط فرمان", "شل"],
    ),
    AppEntry(
        id="files",
        display_name="File Manager",
        command="nautilus",
        aliases=["files", "nautilus", "file manager", "فایل منیجر", "مدیریت فایل", "فایلها", "فایل ها"],
    ),
    AppEntry(
        id="calculator",
        display_name="Calculator",
        command="gnome-calculator",
        aliases=["calculator", "calc", "gnome-calculator", "kcalc", "ماشین حساب", "حساب کتاب"],
    ),
    AppEntry(
        id="text_editor",
        display_name="Text Editor",
        command="gedit",
        aliases=["gedit", "text editor", "gnome-text-editor", "ویرایشگر متن", "تکست ادیتور", "نوت پد"],
    ),
    AppEntry(
        id="vlc",
        display_name="VLC Media Player",
        command="vlc",
        aliases=["vlc", "vlc media player", "وی ال سی", "مدیا پلیر"],
    ),
    AppEntry(
        id="gimp",
        display_name="GIMP Image Editor",
        command="gimp",
        aliases=["gimp", "گیمپ", "ویرایش عکس"],
    ),
    AppEntry(
        id="settings",
        display_name="Settings",
        command="gnome-control-center",
        aliases=["settings", "gnome-control-center", "تنظیمات", "کنترل سنتر"],
    ),
    AppEntry(
        id="spotify",
        display_name="Spotify",
        command="spotify",
        aliases=["spotify", "اسپاتیفای", "اسپاتی فای"],
    ),
    AppEntry(
        id="thunderbird",
        display_name="Thunderbird Mail",
        command="thunderbird",
        aliases=["thunderbird", "ایمیل", "تاندربرد"],
    ),
    AppEntry(
        id="libreoffice",
        display_name="LibreOffice",
        command="libreoffice",
        aliases=["libreoffice", "لیبره آفیس", "آفیس"],
    ),
]


class ApplicationRegistry:
    """Manages application discovery, registry, and allowlist validation."""

    def __init__(self) -> None:
        self._entries: dict[str, AppEntry] = {}
        self._alias_map: dict[str, str] = {}
        self._load_builtins()
        self._discover_desktop_apps()

    def _load_builtins(self) -> None:
        """Register built-in application profiles."""
        for app in BUILTIN_APPS:
            self.register(app)

    def register(self, app: AppEntry) -> None:
        """Register an application entry and its aliases."""
        self._entries[app.id] = app
        # Primary lookup key
        self._alias_map[app.id.lower()] = app.id
        self._alias_map[app.display_name.lower()] = app.id
        self._alias_map[app.command.lower()] = app.id

        # Register all aliases
        for alias in app.aliases:
            cleaned = alias.strip().lower()
            if cleaned:
                self._alias_map[cleaned] = app.id

    def _discover_desktop_apps(self) -> None:
        """Scan system .desktop files on Ubuntu to discover installed apps dynamically."""
        desktop_dirs = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local" / "share" / "applications",
        ]

        for d in desktop_dirs:
            if not d.is_dir():
                continue
            try:
                for f in d.glob("*.desktop"):
                    self._parse_desktop_file(f)
            except Exception as e:
                logger.debug("Error reading desktop files from %s: %s", d, e)

    def _parse_desktop_file(self, filepath: Path) -> None:
        """Extract Name, Exec, and Icon from a .desktop file."""
        try:
            name: Optional[str] = None
            exec_cmd: Optional[str] = None
            icon: Optional[str] = None
            nodisplay = False

            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Name=") and name is None:
                        name = line[5:].strip()
                    elif line.startswith("Exec=") and exec_cmd is None:
                        raw_exec = line[5:].strip()
                        exec_cmd = parse_desktop_exec_line(raw_exec)
                    elif line.startswith("Icon=") and icon is None:
                        icon = line[5:].strip()
                    elif line.startswith("NoDisplay=true"):
                        nodisplay = True

            if nodisplay or not name or not exec_cmd:
                return

            # Check if binary actually exists in PATH or is an absolute file
            if not shutil.which(exec_cmd) and not (os.path.isabs(exec_cmd) and os.path.isfile(exec_cmd)):
                return

            app_id = filepath.stem.lower()
            if app_id not in self._entries:
                entry = AppEntry(
                    id=app_id,
                    display_name=name,
                    command=exec_cmd,
                    aliases=[name.lower(), app_id],
                    desktop_file=str(filepath),
                    icon=icon,
                )
                self.register(entry)
        except Exception as e:
            logger.debug("Failed parsing desktop file %s: %s", filepath, e)

    def find(self, query: str, safe_execution: Optional[bool] = None) -> Optional[AppEntry]:
        """
        Find an application by query string (name, alias, or command).

        Enforces safe_execution policy:
        - When safe_execution=True (default): Only matches against allowlisted/registered
          applications (built-ins and discovered .desktop entries).
        - When safe_execution=False: If not in allowlist, checks if query is an installed
          executable in PATH (provided it is not in DANGEROUS_COMMANDS).
        """
        if not query:
            return None

        cleaned = query.strip().lower()

        # Proactively reject dangerous system commands from ever becoming an AppEntry
        if cleaned in DANGEROUS_COMMANDS or any(cleaned == d for d in DANGEROUS_COMMANDS):
            return None

        # 1. Direct alias match in registered allowlist
        if cleaned in self._alias_map:
            return self._entries[self._alias_map[cleaned]]

        # 2. Match without spaces or hyphens
        normalized_q = cleaned.replace(" ", "").replace("-", "")
        for alias, app_id in self._alias_map.items():
            if alias.replace(" ", "").replace("-", "") == normalized_q:
                return self._entries[app_id]

        # 3. Partial / substring match in registered allowlist
        for app in self._entries.values():
            if cleaned == app.display_name.lower() or cleaned == app.id:
                return app

        # 4. Check safe_execution semantics
        if safe_execution is None:
            safe_execution = get_config().safe_execution

        # If strict safe_execution is active, reject arbitrary PATH queries not in allowlist
        if safe_execution:
            return None

        # When safe_execution is explicitly relaxed: allow non-destructive installed binaries
        exe_path = shutil.which(cleaned)
        if exe_path and not any(cleaned == cmd for cmd in DANGEROUS_COMMANDS):
            return AppEntry(
                id=cleaned,
                display_name=cleaned.capitalize(),
                command=cleaned,
                aliases=[cleaned],
            )

        return None

    def search_candidates(self, query: str) -> list[AppEntry]:
        """Return list of candidate applications matching query for disambiguation."""
        if not query:
            return []

        cleaned = query.strip().lower()
        results: list[AppEntry] = []
        seen: set[str] = set()

        for app in self._entries.values():
            if app.id in seen:
                continue
            if (
                cleaned in app.id
                or cleaned in app.display_name.lower()
                or any(cleaned in a for a in app.aliases)
            ):
                results.append(app)
                seen.add(app.id)

        return results

    def list_installed_apps(self) -> list[AppEntry]:
        """List all applications currently detected as installed on the system."""
        return [app for app in self._entries.values() if app.is_installed()]


_GLOBAL_REGISTRY: Optional[ApplicationRegistry] = None


def get_application_registry() -> ApplicationRegistry:
    """Retrieve the global ApplicationRegistry instance."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ApplicationRegistry()
    return _GLOBAL_REGISTRY
