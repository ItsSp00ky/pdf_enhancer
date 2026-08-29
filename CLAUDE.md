# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A cross-platform (Windows & Linux / Fedora) desktop app (CustomTkinter) that turns photographed/scanned PDFs or loose images into clean, high-contrast, deskewed black-and-white PDFs. Everything lives in a single file: `main.py`.

The git repo root is `python_version/`. Sibling directories `../cpp_version/` and `../phone_app/` are **not** part of this repo — don't touch them unless asked.

## Commands

```bash
# Dependencies are managed by uv. `.python-version` pins 3.13; uv fetches it if missing.
uv sync                 # runtime deps only, into .venv/
uv sync --all-groups    # + the dev group (pyinstaller), needed to build

# Run application
uv run python main.py

# Build distributable executable (Windows .exe or Linux binary)
uv run pyinstaller main.spec

# Linux / Fedora quick setup & build scripts:
./install_linux.sh      # Installs desktop entry, icon, and syncs environment
./run_linux.sh          # Direct runner
./build_linux.sh        # PyInstaller build for Linux
```

`pyproject.toml` + `uv.lock` are the source of truth; both belong in version control. `requirements.txt` is a legacy unpinned mirror kept for anyone without uv — if you change a dependency, change `pyproject.toml` first and re-run `uv sync`.

No activation step is needed: `uv run` resolves `.venv/` itself. If you prefer an activated shell, `.\.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate` (Linux) works as usual.

`main.spec` is tracked in version control and configured for builds: it collects `customtkinter`, `tkinterdnd2`, and `pypdfium2`, prunes foreign OS binaries and redundant Tcl encoding files, and bundles `scanner.ico` and `scanner.png`.

## Architecture

**Pipeline:** `iter_source_images()` normalizes the selection into a stream of `(index, total, pil_image)` → `process_single_page()` → `PIL.Image` mode `"1"` → accumulate in `processed_pages` → `processed_pages[0].save(..., save_all=True, append_images=...)`. Pillow's multi-page save is the PDF *writer*; `pypdfium2` (Google PDFium) rasterizes input PDF pages. Pages are saved 1-bit (the data is already binary) so Pillow applies CCITT G4 — roughly 20x smaller than saving mode `"L"`.

**Input kind is auto-detected per file, not globally.** There is no mode toggle: `is_pdf()` classifies each path by extension, and `iter_source_images()` walks the selection in order, expanding each PDF into its pages and each image into one page. A selection may freely mix the two — a PDF plus three photos concatenates into one output PDF. `count_source_pages()` pre-walks the selection to get `total` for the progress line, which means input PDFs are opened twice per run (cheap next to rasterizing). Anything that needs to branch on kind should call `is_pdf()` rather than reintroducing a mode flag.

**`process_single_page()`** is the whole CV algorithm (implemented via Pillow and NumPy for maximum performance and minimum binary footprint):
1. `find_page_quad()` downscales to 800px height (never upscales) — detection runs on the small image, the corners are divided by `scale` and the warp is applied to the full-res original.
2. Vectorized RGB/HSV "white-ish" mask (`V >= 100` and `S <= 60`) + open/close morphology via Pillow's C filters.
3. Graham scan convex hull + Douglas-Peucker polygon simplification at 2% of perimeter; accepted as the page only if it has exactly 4 points **and** covers >15% of the frame. Otherwise the image passes through uncropped.
4. `four_point_transform` (Pillow `Image.Transform.QUAD` with bilinear resampling) then adaptive Gaussian threshold (equivalent to block 21, C 10) + `MedianFilter(3)`. Output is single-channel 1-bit binary — color is intentionally discarded.

**Threading:** all rasterizing/processing runs on `daemon=True` threads (`run_preview`, `run_pipeline`). Tkinter is not thread-safe, so two rules hold throughout:
- Widget values are **snapshotted on the main thread** and passed in as thread args (mode, paths, DPI). Workers never read a widget.
- Every UI mutation from a worker goes through `run_on_ui()`, which drops the update once `is_closing` is set and swallows the `TclError`/`RuntimeError` that a teardown race produces.

**Drag and drop:** `ScannerApp` multiply inherits `ctk.CTk` *and* `TkinterDnD.DnDWrapper`; `TkinterDnD._require(self)` must run before `drop_target_register`. The whole block is wrapped in try/except so the app still launches when the tkdnd binaries are missing (common when a build drops them). Dropped paths are split with `self.tk.splitlist` to survive spaces.

**PyInstaller:** any bundled asset must be read through `resource_path()` (`sys._MEIPASS`), not a bare relative path.

## Conventions worth preserving

- Accepted extensions live in `IMAGE_EXTENSIONS`/`SUPPORTED_EXTENSIONS`; the drop handler and the browse dialog's `BROWSE_FILETYPES` both derive from them, so adding a format is a one-line change.
- Button state changes go through `set_busy()`, not ad-hoc `configure` calls, so labels/states can't drift apart.
- `run_pipeline`/`run_preview` use `try/except/else` so there is exactly one success path and one failure path, and the UI is always re-enabled.
