<div id="top" align="center">

# 📄 PDF Enhancer
### *Transform Scanned PDFs into Professional-Quality Documents*

[![Last Commit](https://img.shields.io/github/last-commit/ItsSp00ky/pdf_enhancer?style=flat&logo=git&logoColor=white&color=0080ff)](https://github.com/ItsSp00ky/pdf_enhancer/commits/main)
[![Top Language](https://img.shields.io/github/languages/top/ItsSp00ky/pdf_enhancer?style=flat&color=0080ff)](https://github.com/ItsSp00ky/pdf_enhancer)
[![License](https://img.shields.io/github/license/ItsSp00ky/pdf_enhancer?style=flat&color=0080ff)](LICENSE)

*Built with:*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?style=flat&logo=opencv&logoColor=white)
![Gradio](https://img.shields.io/badge/Gradio-Web_Interface-FB923C?style=flat&logo=gradio&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-Array_Processing-013243?style=flat&logo=numpy&logoColor=white)

</div>

---

## 📖 Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Demo](#demo)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

---

## 🧐 Overview

**PDF Enhancer** is an open-source tool designed to rescue low-quality scanned documents. Whether you have dark backgrounds, skewed pages, or faint text from a mobile photo, this tool uses advanced computer vision to reconstruct a clean, print-ready PDF.

It runs entirely locally on your machine—no internet required, ensuring complete privacy for your sensitive documents.

---

## ✨ Key Features

* **🚀 Memory Efficient:** Uses Python Generators to process large PDFs page-by-page, preventing RAM crashes on huge files.
* **📐 Smart Cropping:** Automatically detects document borders and straightens skewed pages. If no border is found, it intelligently preserves the full page.
* **🎨 Professional Contrast:** Uses **CLAHE** (Contrast Limited Adaptive Histogram Equalization) instead of harsh binary thresholds, preserving signatures and stamps while making text crisp.
* **🧹 Noise Reduction:** Automatically removes "salt and pepper" noise common in mobile scans.
* **🌐 Simple Interface:** A clean web UI powered by **Gradio**—no command line knowledge needed after installation.

---

## 🖼️ Demo

*(Add a screenshot here! It makes a huge difference. Example: "Original (Left) vs Enhanced (Right)")*

> *Note: This tool runs on `localhost`, meaning your files never leave your computer.*

---

## ⚙️ Installation

### Prerequisites
* Python 3.8 or higher
* pip (Python Package Manager)

### Steps

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/ItsSp00ky/pdf_enhancer.git](https://github.com/ItsSp00ky/pdf_enhancer.git)
    ```

2.  **Navigate to the directory:**
    ```bash
    cd pdf_enhancer
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚀 Usage

1.  Run the application:
    ```bash
    python pdf_enhancer.py
    ```

2.  Open your browser and go to the local URL shown in the terminal (usually):
    ```
    [http://127.0.0.1:7860](http://127.0.0.1:7860)
    ```

3.  Upload your PDF, adjust the DPI slider, and click **Submit**!

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

**Ahmed Gali** © 2025
