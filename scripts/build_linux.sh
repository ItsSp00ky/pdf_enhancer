#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "==========================================="
echo "   PDF Enhancer C++ - Linux / Fedora Build "
echo "==========================================="

# Check/Install build dependencies on Fedora/Debian/Arch
if command -v dnf &>/dev/null; then
    echo "Detected Fedora / RHEL. Ensuring build dependencies are installed..."
    sudo dnf install -y cmake gcc-c++ qt6-qtbase-devel qt6-qtpdf-devel opencv-devel
elif command -v apt-get &>/dev/null; then
    echo "Detected Debian / Ubuntu. Ensuring build dependencies are installed..."
    sudo apt-get update
    sudo apt-get install -y cmake g++ qt6-base-dev qt6-pdf-dev libopencv-dev
elif command -v pacman &>/dev/null; then
    echo "Detected Arch Linux. Ensuring build dependencies are installed..."
    sudo pacman -S --needed --noconfirm cmake gcc qt6-base qt6-pdf opencv
fi

# Configure & Build
mkdir -p build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j$(nproc 2>/dev/null || echo 4)

echo "==========================================="
echo "Build complete!"
echo "Binary available at: $SCRIPT_DIR/build/pdf_enhancer_cpp"
echo "Run with: ./build/pdf_enhancer_cpp"
echo "==========================================="
