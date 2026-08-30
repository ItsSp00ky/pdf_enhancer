# AI Editing Guide (Maintainers)

This file helps future AI/code assistants edit this project safely and consistently.

## Primary Goals

- Preserve the document enhancement behavior from the Python version.
- Keep processing logic isolated from UI so mobile migration stays simple.
- Prefer minimal, focused edits over broad refactors.

## Architecture Overview

- `src/DocumentProcessor.*`
  - Core processing and file conversion logic.
  - OpenCV pipeline lives here.
  - Keep this module UI-agnostic.
- `src/MainWindow.*`
  - Qt Widgets desktop UI only.
  - Handles file selection, preview action, async processing trigger, and save flow.
- `src/main.cpp`
  - App entry point only.

## High-Risk Areas

- `processSinglePage()` in `DocumentProcessor.cpp`
  - Changes here directly affect output quality.
  - Do not alter thresholds/constants unless intentionally tuning quality.
- PDF load/save methods
  - Qt API differences between versions can break build (`QPdfDocument::Error::None` in Qt 6.8+).
- Background processing in `MainWindow.cpp`
  - Keep heavy work off UI thread.

## Safe Edit Guidelines

- Prefer adding helper functions instead of rewriting large blocks.
- Keep function signatures stable unless necessary.
- Do not mix UI code into `DocumentProcessor.*`.
- Keep ASCII text in source/docs unless there is a strong reason.
- After C++ edits, run configure + build before finalizing.

## Build/Environment Notes (Windows)

- Qt path example: `C:/Qt/6.8.3/msvc2022_64`
- OpenCV path example: `C:/opencv/build`
- For some new MSVC toolsets, OpenCV prebuilt packages may require `OpenCV_RUNTIME=vc16`.
- Preferred automation entrypoints:
  - `scripts/build.ps1`
  - `scripts/release.ps1`
  - `CMakePresets.json` (`windows-release`)

## Verification Checklist

1. Configure:
   - `cmake -S . -B build -DCMAKE_PREFIX_PATH="C:/Qt/6.8.3/msvc2022_64" -DOpenCV_DIR="C:/opencv/build"`
2. Build:
   - `cmake --build build --config Release`
   - or `cmake --build --preset windows-release`
3. Runtime:
   - Ensure Qt DLLs are deployed (`windeployqt`)
   - Ensure OpenCV runtime DLL is beside executable
4. Functional smoke test:
   - Load one PDF
   - Preview first page
   - Convert and save output PDF
5. CI check:
   - Ensure `.github/workflows/windows-ci.yml` passes on PR/push

## Suggested Future Enhancements

- Add unit tests for geometry functions and thresholding pipeline.
- Add a CLI mode using `DocumentProcessor` for batch processing.
- Add structured config for quality presets (scan, photo, receipt, textbook).
