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

## ✨ Key Features

* **🎨 Professional Enhancement:** Automatically converts shadowed or gray backgrounds into pure white while maintaining crisp, black text.
* **📐 Smart Geometry Correction:** Detects document borders, crops excess background, and straightens tilted (skewed) pages using perspective transforms.
* **👁️ Real-time Preview:** Integrated preview window allows you to see the results of the first page before processing the entire document.
* **⚡ Multi-threaded Engine:** Conversion runs on a background thread to keep the interface responsive during heavy processing.
* **📦 Resolution Control:** Adjustable DPI settings (100–400) to give you control over the balance between quality and file size.
* **🚀 Modern Desktop UI:** Built with `customtkinter` for a sleek, user-friendly dark-mode experience.

---

## 🖼️ Preview



---

## ⚙️ Installation

### Prerequisites
* Python 3.8 or higher
* `pip` (Python Package Manager)

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ItsSp00ky/pdf_enhancer.git
   cd pdf_enhancer

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

3. **Run the application:**
   ```bash
   python main.py

---

## 🚀 Usage

1. **Browse:** Select your input PDF file.
2. **Adjust:** Set your desired Scan Quality (DPI) using the slider.
3. **Preview:** Use the "Preview First Page" button to check the result.
4. **Save:** Click "Convert & Save" to choose your output location. The final document will open automatically upon completion.

---

## 📜 License

MIT License - Copyright (c) 2025 Ahmed Gali.
See the [LICENSE](LICENSE) file for more details.

<div align="center">
  Developed by <a href="https://github.com/ItsSp00ky">Ahmed Gali</a>
</div>
