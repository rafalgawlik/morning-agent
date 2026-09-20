#!/bin/zsh
# Launch Morning Agent (the menu bar app).
# On first run it creates a virtual environment and installs dependencies.

set -e
SCRIPT_DIR="${0:A:h}"
VENV="$SCRIPT_DIR/.venv"
PY="/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"

# Fallback if the path above does not exist.
[[ -x "$PY" ]] || PY="$(command -v python3)"

if [[ ! -d "$VENV" ]]; then
  echo "Creating virtual environment in $VENV …"
  "$PY" -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip >/dev/null
  "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

# Set PYTHONPATH explicitly so the package is found regardless of the start dir.
export PYTHONPATH="$SCRIPT_DIR"
exec "$VENV/bin/python" -m morning_agent
