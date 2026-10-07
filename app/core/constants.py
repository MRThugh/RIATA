"""
Core constants for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)
"""

from typing import Final

__version__: Final[str] = "0.2.0"
APP_NAME: Final[str] = "R.I.A.T.A"
APP_FULL_NAME: Final[str] = "Responsive Intent Automation & Task Assistant"
APP_AUTHOR: Final[str] = "Ali Kamrani (MRThugh)"
APP_GITHUB: Final[str] = "https://github.com/MRThugh/RIATA"
APP_LICENSE: Final[str] = "MIT"

# Intent identifiers
INTENT_OPEN_APPLICATION: Final[str] = "OPEN_APPLICATION"
INTENT_CLOSE_APPLICATION: Final[str] = "CLOSE_APPLICATION"
INTENT_OPEN_URL: Final[str] = "OPEN_URL"
INTENT_OPEN_FOLDER: Final[str] = "OPEN_FOLDER"
INTENT_OPEN_FILE: Final[str] = "OPEN_FILE"
INTENT_CREATE_FILE: Final[str] = "CREATE_FILE"
INTENT_DELETE_FILE: Final[str] = "DELETE_FILE"
INTENT_CREATE_FOLDER: Final[str] = "CREATE_FOLDER"
INTENT_DELETE_FOLDER: Final[str] = "DELETE_FOLDER"
INTENT_PLAY_MUSIC: Final[str] = "PLAY_MUSIC"
INTENT_OPEN_TERMINAL: Final[str] = "OPEN_TERMINAL"
INTENT_OPEN_FILE_MANAGER: Final[str] = "OPEN_FILE_MANAGER"
INTENT_OPEN_SETTINGS: Final[str] = "OPEN_SETTINGS"
INTENT_SHOW_SYSTEM_INFO: Final[str] = "SHOW_SYSTEM_INFO"
INTENT_TAKE_SCREENSHOT: Final[str] = "TAKE_SCREENSHOT"
INTENT_EXIT_APPLICATION: Final[str] = "EXIT_APPLICATION"
INTENT_UNKNOWN: Final[str] = "UNKNOWN"
INTENT_CLARIFY: Final[str] = "CLARIFY"
INTENT_CLARIFY_AMBIGUITY: Final[str] = "CLARIFY_AMBIGUITY"
INTENT_CONFIRM: Final[str] = "CONFIRM"
INTENT_CANCEL: Final[str] = "CANCEL"
INTENT_RESET_CONTEXT: Final[str] = "RESET_CONTEXT"

ALL_INTENTS: Final[tuple[str, ...]] = (
    INTENT_OPEN_APPLICATION,
    INTENT_CLOSE_APPLICATION,
    INTENT_OPEN_URL,
    INTENT_OPEN_FOLDER,
    INTENT_OPEN_FILE,
    INTENT_CREATE_FILE,
    INTENT_DELETE_FILE,
    INTENT_CREATE_FOLDER,
    INTENT_DELETE_FOLDER,
    INTENT_PLAY_MUSIC,
    INTENT_OPEN_TERMINAL,
    INTENT_OPEN_FILE_MANAGER,
    INTENT_OPEN_SETTINGS,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_TAKE_SCREENSHOT,
    INTENT_EXIT_APPLICATION,
    INTENT_UNKNOWN,
    INTENT_CLARIFY,
    INTENT_CLARIFY_AMBIGUITY,
    INTENT_CONFIRM,
    INTENT_CANCEL,
    INTENT_RESET_CONTEXT,
)

# Confidence thresholds
CONFIDENCE_EXACT: Final[float] = 0.95
CONFIDENCE_HIGH: Final[float] = 0.80
CONFIDENCE_MEDIUM: Final[float] = 0.60
CONFIDENCE_LOW: Final[float] = 0.40

# Supported languages
LANG_PERSIAN: Final[str] = "fa"
LANG_ENGLISH: Final[str] = "en"
LANG_AUTO: Final[str] = "auto"
DEFAULT_LANGUAGE: Final[str] = LANG_AUTO

SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = (LANG_PERSIAN, LANG_ENGLISH)

# Dangerous keywords strictly forbidden from execution
DANGEROUS_COMMANDS: Final[tuple[str, ...]] = (
    "rm",
    "rmdir",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "poweroff",
    "init",
    "sudo",
    "su",
    "chmod",
    "chown",
    ":(){ :|:& };:",
    "> /dev/sda",
    "fdisk",
    "parted",
    "iptables",
    "ufw",
    "deluser",
    "userdel",
)

# Supported music formats
SUPPORTED_AUDIO_EXTENSIONS: Final[tuple[str, ...]] = (
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",
    ".aac",
    ".opus",
)
