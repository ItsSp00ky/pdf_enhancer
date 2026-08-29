param(
    [string]$QtRoot = $env:QT_ROOT,
    [string]$OpenCvBin = $env:OPENCV_BIN
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($QtRoot)) {
    $QtRoot = "C:/Qt/6.8.3/msvc2022_64"
}

if ([string]::IsNullOrWhiteSpace($OpenCvBin)) {
    $OpenCvBin = "C:/opencv/build/x64/vc16/bin"
}

$exePath = ".\build\Release\pdf_enhancer_cpp.exe"
if (-not (Test-Path $exePath)) {
    throw "Executable not found at $exePath. Run scripts/build.ps1 first."
}

$windeployqt = Join-Path $QtRoot "bin/windeployqt.exe"
if (-not (Test-Path $windeployqt)) {
    throw "windeployqt.exe not found under QT_ROOT: $QtRoot"
}

& $windeployqt --release --no-translations $exePath
if ($LASTEXITCODE -ne 0) { throw "windeployqt failed." }

$opencvDll = Join-Path $OpenCvBin "opencv_world4120.dll"
if (-not (Test-Path $opencvDll)) {
    throw "OpenCV runtime DLL not found: $opencvDll"
}

Copy-Item $opencvDll ".\build\Release\" -Force

$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$zipPath = ".\build\pdf_enhancer_cpp-win64-$stamp.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path ".\build\Release\*" -DestinationPath $zipPath
Write-Host "Release package created: $zipPath"
