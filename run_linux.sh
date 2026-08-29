#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v uv &>/dev/null; then
    exec uv run python main.py "$@"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    exec "$SCRIPT_DIR/.venv/bin/python" main.py "$@"
else
    echo "Virtual environment not detected. Running install_linux.sh..."
    bash "$SCRIPT_DIR/install_linux.sh"
    exec "$SCRIPT_DIR/.venv/bin/python" main.py "$@"
fi
