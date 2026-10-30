#!/bin/bash
set -euo pipefail

# Only needed in Claude Code cloud sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Backend deps plus pytest (installs into system Python, so no hash check:
# pip is a fast no-op when everything is already satisfied)
python -m pip install --quiet -r backend/requirements-dev.txt
