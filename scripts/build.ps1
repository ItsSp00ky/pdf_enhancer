param(
    [string]$QtRoot = $env:QT_ROOT,
    [string]$OpenCvDir = $env:OPENCV_DIR
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($QtRoot)) {
    $QtRoot = "C:/Qt/6.8.3/msvc2022_64"
}

if ([string]::IsNullOrWhiteSpace($OpenCvDir)) {
    $OpenCvDir = "C:/opencv/build"
}

Write-Host "Using QT_ROOT=$QtRoot"
Write-Host "Using OPENCV_DIR=$OpenCvDir"

cmake -S . -B build -DCMAKE_PREFIX_PATH="$QtRoot" -DOpenCV_DIR="$OpenCvDir"
if ($LASTEXITCODE -ne 0) { throw "CMake configure failed." }

cmake --build build --config Release
if ($LASTEXITCODE -ne 0) { throw "Build failed." }

Write-Host "Build complete: .\build\Release\pdf_enhancer_cpp.exe"
