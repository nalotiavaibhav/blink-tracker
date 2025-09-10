<#
Build standalone Windows executable for WaW Desktop App.
Prerequisites:
 - Activate virtual environment with required deps (PyQt6, requests, etc.)
 - pip install pyinstaller pillow
Usage:
  powershell -ExecutionPolicy Bypass -File .\build_windows_exe.ps1
Outputs dist/WellnessAtWork/WellnessAtWork.exe with icon.
#>

$ErrorActionPreference = 'Stop'

Write-Host "==> Ensuring icon exists"
if (-not (Test-Path assets/app.ico)) {
    python tools/generate_icon.py
}

Write-Host "==> Running PyInstaller"
pyinstaller --noconfirm `
  --name "WellnessAtWork" `
  --icon assets/app.ico `
  --add-data "assets;assets" `
  --hidden-import "cv2" `
  --hidden-import "mediapipe" `
  --hidden-import "psutil" `
  --hidden-import "PyQt6" `
  --collect-all mediapipe `
  --collect-all cv2 `
  --collect-submodules mediapipe `
  desktop/main.py

Write-Host "==> Build complete. EXE at dist/WellnessAtWork/WellnessAtWork.exe"
