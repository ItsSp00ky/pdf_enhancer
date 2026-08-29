#!/usr/bin/env bash
set -e

# PDF Enhancer - Linux & Fedora Automated Installer
# Copyright (c) 2025-2026 Ahmed Gali

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/32x32/apps"

echo "==========================================="
echo "       PDF Enhancer - Linux Setup          "
echo "==========================================="

# 1. Check for Python & Tkinter dependencies on Fedora / Linux
echo "[1/4] Checking system dependencies..."
if command -v dnf &>/dev/null; then
    echo "Detected Fedora / RHEL system."
    if ! rpm -q python3-tkinter &>/dev/null; then
        echo "Installing python3-tkinter (requires sudo)..."
        sudo dnf install -y python3-tkinter
    fi
elif command -v apt-get &>/dev/null; then
    echo "Detected Debian / Ubuntu system."
    if ! dpkg -s python3-tk &>/dev/null; then
        echo "Installing python3-tk (requires sudo)..."
        sudo apt-get update && sudo apt-get install -y python3-tk
    fi
elif command -v pacman &>/dev/null; then
    echo "Detected Arch Linux system."
    if ! pacman -Qi tk &>/dev/null; then
        echo "Installing tk (requires sudo)..."
        sudo pacman -S --noconfirm tk
    fi
fi

# 2. Setup Python environment (Prefer uv, fallback to venv)
echo "[2/4] Setting up Python virtual environment..."
cd "$SCRIPT_DIR"

if command -v uv &>/dev/null; then
    echo "Using uv for high-speed environment synchronization..."
    uv sync
    RUNNER_CMD="uv run --project \"$SCRIPT_DIR\" python \"$SCRIPT_DIR/main.py\""
else
    echo "uv not found; creating standard virtual environment (.venv)..."
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    RUNNER_CMD="\"$SCRIPT_DIR/.venv/bin/python\" \"$SCRIPT_DIR/main.py\""
fi

# 3. Install desktop launcher and icon
echo "[3/4] Installing application shortcut & icons..."
mkdir -p "$BIN_DIR" "$APPS_DIR" "$ICONS_DIR"

# Install icon
if [ -f "$SCRIPT_DIR/scanner.png" ]; then
    cp "$SCRIPT_DIR/scanner.png" "$ICONS_DIR/pdf-enhancer.png"
fi

# Generate CLI launcher script in ~/.local/bin/pdf-enhancer
cat <<EOF > "$BIN_DIR/pdf-enhancer"
#!/usr/bin/env bash
if command -v uv &>/dev/null; then
    exec uv run --project "$SCRIPT_DIR" python "$SCRIPT_DIR/main.py" "\$@"
else
    exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/main.py" "\$@"
fi
EOF
chmod +x "$BIN_DIR/pdf-enhancer"

# Generate .desktop file
cat <<EOF > "$APPS_DIR/pdf-enhancer.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=PDF Enhancer
GenericName=Document Scanner & Enhancer
Comment=Turn photographed or scanned PDFs and images into clean, deskewed, high-contrast PDFs
Exec=$BIN_DIR/pdf-enhancer %F
Icon=pdf-enhancer
Terminal=false
Categories=Office;Graphics;Scanning;Utility;
MimeType=application/pdf;image/jpeg;image/png;image/tiff;image/bmp;
StartupNotify=true
EOF
chmod +x "$APPS_DIR/pdf-enhancer.desktop"

# Update desktop database if tool is present
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

# 4. Done
echo "[4/4] Setup complete!"
echo "==========================================="
echo "PDF Enhancer is now installed on your system!"
echo ""
echo "You can launch it by:"
echo "  1. Searching 'PDF Enhancer' in your application menu (GNOME / KDE)"
echo "  2. Running 'pdf-enhancer' in terminal (ensure ~/.local/bin is in PATH)"
echo "  3. Running './run_linux.sh' from this directory"
echo "==========================================="
