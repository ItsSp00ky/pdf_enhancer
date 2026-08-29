# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A cross-platform (Windows & Linux) desktop application (C++17, Qt 6, OpenCV 4) that transforms photographed or scanned PDFs and images into clean, deskewed, high-contrast, print-ready black-and-white PDFs.

The legacy Python implementation is archived on the [`python-legacy`](https://github.com/ItsSp00ky/pdf_enhancer/tree/python-legacy) branch.

## Build Commands

### Windows (MSVC 2022 + Qt 6 + OpenCV)

```powershell
# Configure & Build Release
cmake -S . -B build -DCMAKE_PREFIX_PATH="C:/Qt/6.8.3/msvc2022_64" -DOpenCV_DIR="C:/opencv/build"
cmake --build build --config Release

# Helper scripts
.\scripts\build.ps1     # Build executable
.\scripts\release.ps1   # Deploy Qt runtime (windeployqt) and zip package
```

### Linux (Ubuntu / Fedora / Arch)

```bash
# Ubuntu / Debian dependencies
sudo apt-get install -y cmake g++ qt6-base-dev qt6-pdf-dev libopencv-dev

# Fedora dependencies
sudo dnf install -y cmake gcc-c++ qt6-qtbase-devel qt6-qtpdf-devel opencv-devel

# Build Release
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j$(nproc)

# Helper script
./scripts/build_linux.sh
```

## Architecture

- **`src/main.cpp`**: Qt 6 application entry point.
- **`src/MainWindow.h / .cpp`**: Main GUI window using Qt 6 Widgets (`QFileDialog`, `QDragEnterEvent`, `QDropEvent`, `QSlider`, `QProgressBar`).
  - Implements drag-and-drop file ingestion, dynamic DPI resolution updates, and asynchronous previews.
  - Keeps UI responsive by executing PDF loading, image conversion, and OpenCV enhancement via `QtConcurrent::run`.
- **`src/DocumentProcessor.h / .cpp`**: Core image processing & geometry pipeline:
  1. **Page Detection & Deskewing (`processSinglePage`)**: Detects white paper boundaries using contour approximation and Graham convex hull, applying 4-point perspective warp.
  2. **Adaptive Binarization**: High-contrast adaptive Gaussian thresholding with median noise reduction.
  3. **PDF Rendering & Generation**: Multi-page PDF rasterization and rendering using `QPdfDocument` and high-res vector output via `QPdfWriter` / `QPainter`.

## Conventions

- Keep all business logic and image transformation in `DocumentProcessor`, keeping `MainWindow` focused on UI and threading.
- Use `QtConcurrent::run` with `QFutureWatcher` for long-running document processing tasks to keep the UI loop unblocked.
- All file paths and cross-platform operations should use `QFileInfo` and `QDir::toNativeSeparators`.
