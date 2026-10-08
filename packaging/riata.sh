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

# Prefer virtual environment interpreter if currently activated by user
if [ -n "${VIRTUAL_ENV}" ] && [ -x "${VIRTUAL_ENV}/bin/python3" ]; then
    exec "${VIRTUAL_ENV}/bin/python3" "${ENTRYPOINT}" "$@"
elif [ -x "/usr/bin/python3" ]; then
    exec /usr/bin/python3 "${ENTRYPOINT}" "$@"
else
    exec python3 "${ENTRYPOINT}" "$@"
fi
