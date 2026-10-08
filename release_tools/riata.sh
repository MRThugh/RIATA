#!/bin/bash
# R.I.A.T.A — Responsive Intent Automation & Task Assistant
# Native Linux Entrypoint Wrapper
# Author: Ali Kamrani (MRThugh)

set -e

APP_DIR="/usr/lib/riata"
ENTRYPOINT="${APP_DIR}/main.py"

if [ ! -f "${ENTRYPOINT}" ]; then
    echo "Error: RIATA application entrypoint not found at ${ENTRYPOINT}" >&2
    exit 1
fi

export PYTHONPATH="${APP_DIR}:${PYTHONPATH}"

# Determine Python interpreter to execute RIATA
PYTHON_EXEC=""
if [ -x "${APP_DIR}/venv/bin/python3" ]; then
    PYTHON_EXEC="${APP_DIR}/venv/bin/python3"
elif [ -n "${VIRTUAL_ENV}" ] && [ -x "${VIRTUAL_ENV}/bin/python3" ]; then
    PYTHON_EXEC="${VIRTUAL_ENV}/bin/python3"
elif [ -x "/usr/bin/python3" ]; then
    PYTHON_EXEC="/usr/bin/python3"
else
    PYTHON_EXEC="$(command -v python3 || echo 'python3')"
fi

# Fast-path for version and help queries (does not require GUI/PySide6)
for arg in "$@"; do
    if [ "$arg" = "-v" ] || [ "$arg" = "--version" ] || [ "$arg" = "-h" ] || [ "$arg" = "--help" ]; then
        exec "${PYTHON_EXEC}" "${ENTRYPOINT}" "$@"
    fi
done

# If user is running non-GUI modes (--cli or --server), execute directly
IS_NON_GUI=0
for arg in "$@"; do
    if [ "$arg" = "--cli" ] || [ "$arg" = "--server" ]; then
        IS_NON_GUI=1
        break
    fi
done

if [ "$IS_NON_GUI" -eq 1 ]; then
    exec "${PYTHON_EXEC}" "${ENTRYPOINT}" "$@"
fi

# For GUI mode (or default when DISPLAY/WAYLAND_DISPLAY is set):
# Check if PySide6 is available before attempting Qt initialization.
HAS_DISPLAY=0
if [ -n "${DISPLAY}" ] || [ -n "${WAYLAND_DISPLAY}" ] || [ "${QT_QPA_PLATFORM}" = "offscreen" ]; then
    HAS_DISPLAY=1
fi

if [ "$HAS_DISPLAY" -eq 1 ] && ! "${PYTHON_EXEC}" -c "import PySide6" >/dev/null 2>&1; then
    echo "============================================================" >&2
    echo "⚠️  RIATA: PySide6 (Qt 6) is required for the desktop GUI." >&2
    echo "============================================================" >&2
    echo "To run the graphical desktop interface, please install PySide6:" >&2
    echo "  sudo apt install python3-pyside6" >&2
    echo "  # or: pip install PySide6" >&2
    echo "" >&2
    echo "Alternatively, you can run RIATA directly in CLI mode:" >&2
    echo "  riata --cli" >&2
    echo "Or in background server mode:" >&2
    echo "  riata --server" >&2
    echo "============================================================" >&2
    exit 1
fi

exec "${PYTHON_EXEC}" "${ENTRYPOINT}" "$@"
