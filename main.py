#!/usr/bin/env python3
"""
R.I.A.T.A — Responsive Intent Automation & Task Assistant
Version: 0.1.0
Author: Ali Kamrani (MRThugh)
GitHub: https://github.com/MRThugh/RIATA
License: MIT
Platform: Ubuntu Linux

Main application entrypoint.
"""

import argparse
import os
import sys

from app.core.config import get_config
from app.core.constants import (
    APP_AUTHOR,
    APP_FULL_NAME,
    APP_NAME,
    __version__,
)
from app.core.logger import get_logger, setup_logger
from app.engine.router import get_intent_router


def run_cli_mode() -> None:
    """Interactive command-line developer mode."""
    logger = get_logger("riata.cli")
    router = get_intent_router()

    print("=" * 60)
    print(f"{APP_NAME} v{__version__} — {APP_FULL_NAME}")
    print(f"Created by {APP_AUTHOR}")
    print("Linux Desktop Intent Engine [CLI Debug Mode]")
    print("Type 'exit' or 'خروج' to quit.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nRIATA > ").strip()
            if not user_input:
                continue

            output = router.process(user_input)
            print(f"\n[Response]\n{output.response_text}")
            if output.intent:
                print(f"[Engine] Intent: {output.intent.name} | Confidence: {output.intent.confidence}")
                if output.intent.entities:
                    print(f"[Engine] Entities: {output.intent.entities}")

            if output.is_exit:
                break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting R.I.A.T.A...")
            break


def run_gui_mode() -> None:
    """Launch modern PySide6 desktop interface."""
    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(f"{APP_NAME} — {APP_FULL_NAME}")
    app.setApplicationVersion(__version__)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="riata",
        description=f"{APP_NAME} v{__version__} — {APP_FULL_NAME} (Author: {APP_AUTHOR})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions without launching processes (dry-run mode)",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run interactive CLI console instead of PySide6 GUI",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{APP_NAME} {__version__}",
    )

    args = parser.parse_args()

    # Configure environment based on arguments
    config = get_config()
    if args.dry_run:
        config.dry_run = True
    if args.debug:
        config.debug = True
        config.logging_level = "DEBUG"

    setup_logger("riata", level=config.logging_level)
    logger = get_logger("riata.main")

    logger.info("Initializing %s v%s by %s", APP_NAME, __version__, APP_AUTHOR)
    if config.dry_run:
        logger.info("Running in DRY-RUN mode: no desktop actions will be executed.")

    # Determine whether GUI can be displayed or if CLI is requested
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if args.cli or not has_display:
        if not has_display and not args.cli:
            logger.info("No DISPLAY or WAYLAND_DISPLAY found; falling back to CLI mode.")
        run_cli_mode()
    else:
        run_gui_mode()


if __name__ == "__main__":
    main()
