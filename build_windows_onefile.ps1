<#
Build a single-file (one EXE) Windows distribution of the WaW Desktop App.
NOTE: Startup will be slower (PyInstaller self-extraction) and file size large due to MediaPipe.
Prerequisites:
  pip install pyinstaller pillow
Usage:
  powershell -ExecutionPolicy Bypass -File .\build_windows_onefile.ps1
Output: dist/WellnessAtWork.exe
#>
$ErrorActionPreference = 'Stop'

Write-Host "==> Ensuring icon exists"
if (-not (Test-Path assets/app.ico)) {
    python tools/generate_icon.py
}

# Optional: reduce size a bit by excluding test modules
$excludes = @(
  'tests',
  'pytest',
  'unittest'
) | ForEach-Object { '--exclude-module', $_ }

Write-Host "==> Building single-file executable (this can take several minutes)"
pyinstaller --noconfirm --onefile --windowed `
  --name "WellnessAtWork" `
  --icon assets/app.ico `
  --add-data "assets;assets" `
  --hidden-import "cv2" `
  --hidden-import "mediapipe" `
  --hidden-import "psutil" `
  --hidden-import "PyQt6" `
  --collect-all mediapipe `
  --collect-all cv2 `
  $excludes `
  desktop/main.py

Write-Host "==> Single-file build complete: dist/WellnessAtWork.exe"
Write-Host "Tip: If SmartScreen warns, choose 'More info' -> 'Run anyway'."
