<div id="top" align="center">

# 📄 PDF Enhancer
### *Transform Scanned PDFs into Professional-Quality Documents*

[![Last Commit](https://img.shields.io/github/last-commit/ItsSp00ky/pdf_enhancer?style=flat&logo=git&logoColor=white&color=0080ff)](https://github.com/ItsSp00ky/pdf_enhancer/commits/main)
[![Top Language](https://img.shields.io/github/languages/top/ItsSp00ky/pdf_enhancer?style=flat&color=0080ff)](https://github.com/ItsSp00ky/pdf_enhancer)
[![License: MIT](https://img.shields.io/badge/License-MIT-0080ff?style=flat)](LICENSE)

*Built with:*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?style=flat&logo=opencv&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-005FB8?style=flat)
![PyMuPDF](https://img.shields.io/badge/PDF-PyMuPDF-FF0000?style=flat)

</div>

---

## 🧐 Overview

**PDF Enhancer** is a specialized desktop application designed to rescue low-quality scanned or photographed documents. Using advanced computer vision techniques, it reconstructs clean, high-contrast, and print-ready PDFs. 

The tool runs **100% locally** on your machine—ensuring complete privacy for your sensitive documents with no internet or server uploads required.

---

## 🚀 Quick Start

### 🪟 Windows
1. Go to the **[Releases](https://github.com/ItsSp00ky/pdf_enhancer/releases)** page.
2. Download the latest `PDF_Enhancer_v1.1.exe` (or `PDF_Enhancer_Windows.exe`).
3. Double-click to run!

### 🐧 Linux (Fedora, Ubuntu, Arch, etc.)
#### Option A: Standalone Binary (No Python setup needed)
1. Go to the **[Releases](https://github.com/ItsSp00ky/pdf_enhancer/releases)** page.
2. Download `PDF_Enhancer_Linux_x86_64` (or `PDF_Enhancer_Linux_x86_64.tar.gz`).
3. Make it executable and run:
   ```bash
   chmod +x PDF_Enhancer_Linux_x86_64
   ./PDF_Enhancer_Linux_x86_64
   ```

#### Option B: Automated Linux / Fedora Installer
Clone and run the automated installer (sets up dependencies, app menu shortcut, and icon):
```bash
git clone https://github.com/ItsSp00ky/pdf_enhancer.git
cd pdf_enhancer/python_version
./install_linux.sh
```
*Note for Fedora users:* If installing manually without the script, install Tkinter via `sudo dnf install python3-tkinter`.

---

## ✨ Key Features

* **🎨 Professional Enhancement:** Automatically converts shadowed or gray backgrounds into pure white while maintaining crisp, black text using adaptive Gaussian thresholding.
* **📐 Smart Geometry Correction:** Automatically detects document borders, crops excess background, and straightens tilted (skewed) pages via 4-point perspective transform.
* **📁 Drag & Drop + Multi-File Support:** Drag and drop files directly into the window. Seamlessly combine multiple PDFs and images (PNG, JPG, TIFF, BMP) into a single unified output PDF.
* **🗜️ Ultra-Compact Output:** Saves output using 1-bit CCITT Group 4 fax compression for crisp text with file sizes up to ~20x smaller than standard scans.
* **👁️ Real-time Preview:** Dedicated preview window lets you inspect the enhanced result of the first page before processing the full document.
* **⚡ Multi-threaded Engine:** Background worker threads keep the UI fluid and responsive with real-time page-by-page progress status.
* **📦 Resolution Control:** Adjustable DPI settings (100–400) to balance scan crispness and processing speed.
* **🔒 100% Local & Private:** Processes all files entirely offline on your computer.

---

## 🖼️ Preview
<img width="696" height="562" alt="Screenshot 2026-02-13 201217" src="https://github.com/user-attachments/assets/915e355c-9925-4e09-b4af-7b946dba6345" />

![1769518501744](https://github.com/user-attachments/assets/2be2a9d0-371d-4fa4-93a0-2c83b73ac876)

---

## ⚙️ Developer Installation

If you prefer to run from source or build the executable yourself:

### Option 1: Using `uv` (Recommended)

[`uv`](https://github.com/astral-sh/uv) is an extremely fast Python package and project manager.

```bash
# 1. Clone the repository
git clone https://github.com/ItsSp00ky/pdf_enhancer.git
cd pdf_enhancer/python_version

# 2. Sync dependencies into virtual environment
uv sync

# 3. Run the application
uv run python main.py

# (Optional) Build standalone executable
uv sync --all-groups
uv run pyinstaller main.spec
```

### Option 2: Using `conda`

```bash
# 1. Create and activate environment from environment.yml
conda env create -f environment.yml
conda activate pdf-enhancer

# 2. Run the application
python main.py
```

### Option 3: Using standard `pip` / `venv`

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

---

## 🚀 Usage

1. **Select Files:** Browse or drag & drop one or more PDF/image files.
2. **Adjust Quality:** Set your desired Scan Quality (DPI) with the slider (200 DPI recommended).
3. **Preview:** Click "👁 Preview First" to inspect the enhanced output before full export.
4. **Convert & Save:** Click "💾 Convert & Save" to choose your output PDF filename. The enhanced document will open automatically upon completion.

---

## 📜 License

MIT License - Copyright (c) 2025 Ahmed Gali.
See the [LICENSE](LICENSE) file for more details.

<div align="center">
  Developed by <a href="https://github.com/ItsSp00ky">Ahmed Gali</a>
</div>
