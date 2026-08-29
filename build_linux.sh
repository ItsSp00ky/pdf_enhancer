#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building PDF Enhancer standalone binary for Linux..."

if command -v uv &>/dev/null; then
    uv sync --all-groups
    uv run pyinstaller main.spec
else
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -r requirements.txt pyinstaller
    pyinstaller main.spec
fi

echo "==========================================="
echo "Build complete!"
echo "Linux executable binary is available at: dist/PDF_Enhancer_v1.1"
echo "==========================================="
