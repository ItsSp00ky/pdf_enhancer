<div id="top" align="center">

# 📄 PDF Enhancer (v2.0 - C++ Edition)
### *High-Performance Desktop Application to Transform Scanned PDFs into Clean, Professional Documents*

[![Last Commit](https://img.shields.io/github/last-commit/ItsSp00ky/pdf_enhancer?style=flat&logo=git&logoColor=white&color=0080ff)](https://github.com/ItsSp00ky/pdf_enhancer/commits/main)
[![Top Language](https://img.shields.io/github/languages/top/ItsSp00ky/pdf_enhancer?style=flat&color=0080ff)](https://github.com/ItsSp00ky/pdf_enhancer)
[![License: MIT](https://img.shields.io/badge/License-MIT-0080ff?style=flat)](LICENSE)

*Built with:*

![C++](https://img.shields.io/badge/C%2B%2B-17-00599C?style=flat&logo=c%2B%2B&logoColor=white)
![Qt](https://img.shields.io/badge/Qt-6.8%2B-41CD52?style=flat&logo=qt&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?style=flat&logo=opencv&logoColor=white)
![CMake](https://img.shields.io/badge/CMake-3.21%2B-064F8C?style=flat&logo=cmake&logoColor=white)

</div>

> [!NOTE]
> **🚀 v2.0 C++ Rewrite:** Starting with version 2.0, PDF Enhancer has been completely rewritten in **C++ and Qt 6** for instant startup, multi-threaded performance, and native binaries.
> 
> *Looking for the legacy Python version?* It is preserved and maintained on the **[`python-legacy`](https://github.com/ItsSp00ky/pdf_enhancer/tree/python-legacy)** branch.

---

## 🧐 Overview

**PDF Enhancer** is a high-performance desktop application designed to rescue low-quality scanned or photographed documents. Using advanced computer vision techniques, it reconstructs clean, deskewed, high-contrast, and print-ready PDFs.

The application runs **100% locally and offline** on your machine—ensuring complete privacy and security for your documents with zero internet or server uploads.

---

## 🚀 Quick Start (Pre-built Binaries)

### 🪟 Windows (x64)
1. Go to the **[Releases](https://github.com/ItsSp00ky/pdf_enhancer/releases)** page.
2. Download the latest `PDF_Enhancer_v2.0_Windows_x64.zip`.
3. Extract the ZIP and double-click `pdf_enhancer_cpp.exe` to run.

### 🐧 Linux (x86_64)
1. Go to the **[Releases](https://github.com/ItsSp00ky/pdf_enhancer/releases)** page.
2. Download `PDF_Enhancer_v2.0_Linux_x86_64.tar.gz`.
3. Extract and run:
   ```bash
   tar -xzf PDF_Enhancer_v2.0_Linux_x86_64.tar.gz
   cd pdf-enhancer-linux
   ./pdf-enhancer
   ```

---

## ✨ Key Features

* **⚡ Native C++ Performance:** Instant startup and fast multi-threaded document processing powered by Qt Concurrent and OpenCV.
* **🎨 High-Contrast Document Cleaning:** Automatically converts dark, shadowed, or yellowed paper backgrounds into pure white while preserving crisp text.
* **📐 4-Point Geometry Deskewing:** Automatically detects document paper boundaries, crops background clutter, and straightens tilted scans.
* **📁 Drag & Drop + Multi-File Support:** Drag and drop files directly onto the window. Supports combining loose images (JPG, PNG, TIFF, BMP) and multi-page PDFs into a single unified PDF.
* **👁️ Interactive Preview:** Preview the deskewed and enhanced result of the first page with real-time resolution and DPI feedback.
* **📦 Resolution Control:** Select your target scan quality from 100 to 400 DPI with calibrated filter scaling.
* **🔒 100% Offline & Private:** All processing happens entirely in memory on your local CPU.

---

## 🖼️ Preview

<div align="center">
  <img width="696" alt="PDF Enhancer Screenshot" src="https://github.com/user-attachments/assets/915e355c-9925-4e09-b4af-7b946dba6345" />
</div>

---

## 🛠️ Building from Source

### Prerequisites

- **C++ Compiler:** MSVC (Visual Studio 2022) on Windows, GCC 11+ or Clang on Linux
- **CMake:** Version 3.21 or newer
- **Qt 6:** Modules `Core`, `Gui`, `Widgets`, `PrintSupport`, `Pdf`, `Concurrent`
- **OpenCV:** 4.x

---

### 🪟 Windows Build

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/ItsSp00ky/pdf_enhancer.git
   cd pdf_enhancer
   ```

2. **Configure & Build with CMake:**
   ```powershell
   cmake -S . -B build `
     -DCMAKE_PREFIX_PATH="C:/Qt/6.8.3/msvc2022_64" `
     -DOpenCV_DIR="C:/opencv/build"
   cmake --build build --config Release
   ```

3. **Deploy & Package (PowerShell script):**
   ```powershell
   .\scripts\release.ps1
   ```

---

### 🐧 Linux Build (Ubuntu / Debian / Fedora / Arch)

1. **Install dependencies:**
   - **Ubuntu / Debian:**
     ```bash
     sudo apt-get update
     sudo apt-get install -y cmake g++ qt6-base-dev qt6-pdf-dev libopencv-dev
     ```
   - **Fedora:**
     ```bash
     sudo dnf install -y cmake gcc-c++ qt6-qtbase-devel qt6-qtpdf-devel opencv-devel
     ```
   - **Arch Linux:**
     ```bash
     sudo pacman -S --needed cmake gcc qt6-base qt6-pdf opencv
     ```

2. **Build with the helper script:**
   ```bash
   chmod +x ./scripts/build_linux.sh
   ./scripts/build_linux.sh
   ```

---

## 📂 Project Layout

```text
pdf_enhancer/
├── src/
│   ├── main.cpp                # Application entry point
│   ├── MainWindow.h/.cpp       # Qt 6 UI implementation & drag-and-drop
│   └── DocumentProcessor.h/.cpp # OpenCV geometry deskewing & PDF rendering
├── scripts/
│   ├── build.ps1               # Windows build helper script
│   ├── release.ps1             # Windows deployment (windeployqt + zip)
│   └── build_linux.sh          # Linux build helper script
├── .github/workflows/
│   └── release.yml             # GitHub Actions CI/CD release workflow
├── CMakeLists.txt              # CMake build configuration
├── CMakePresets.json           # Standard CMake presets
├── scanner.ico / scanner.png   # Application icons
├── README.md                   # Documentation
└── LICENSE                     # MIT License
```

---

## 📜 License

MIT License - Copyright (c) 2025-2026 Ahmed Gali.
See the [LICENSE](LICENSE) file for more details.

<div align="center">
  Developed by <a href="https://github.com/ItsSp00ky">Ahmed Gali</a>
</div>
