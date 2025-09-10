<#
Quick Fix Build Script for Module Import Issues

This script rebuilds the application with proper module structure inclusion.
#>

param (
    [string]$BackendUrl = "http://localhost:8000"
)

$ErrorActionPreference = 'Stop'

Write-Host "========================================================"
Write-Host "Building WaW Desktop App - Module Fix Version"
Write-Host "========================================================"

# Create app_config.json
$config = @{
    apiBase = $BackendUrl
    appVersion = "1.0.0"
    buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
}
$configJson = $config | ConvertTo-Json -Depth 3
Set-Content -Path "app_config.json" -Value $configJson -Encoding UTF8

Write-Host "==> Building with complete module structure"

try {
    pyinstaller --noconfirm `
        --name "WellnessAtWork-Fixed" `
        --console `
        --onefile `
        --icon "assets/app.ico" `
        --paths "." `
        --add-data "assets;assets" `
        --add-data "app_config.json;." `
        --add-data "desktop;desktop" `
        --add-data "shared;shared" `
        --add-data "backend;backend" `
        --hidden-import "desktop" `
        --hidden-import "desktop.main" `
        --hidden-import "desktop.eye_tracker" `
        --hidden-import "shared" `
        --hidden-import "shared.config" `
        --hidden-import "shared.api" `
        --hidden-import "shared.db" `
        --hidden-import "shared.google_oauth" `
        --hidden-import "backend" `
        --hidden-import "backend.models" `
        --hidden-import "backend.main" `
        --hidden-import "backend.emailer" `
        --hidden-import "cv2" `
        --hidden-import "mediapipe" `
        --hidden-import "psutil" `
        --hidden-import "PyQt6" `
        --hidden-import "PyQt6.QtCore" `
        --hidden-import "PyQt6.QtGui" `
        --hidden-import "PyQt6.QtWidgets" `
        --hidden-import "requests" `
        --hidden-import "sqlite3" `
        --hidden-import "dotenv" `
        --hidden-import "pathlib" `
        --hidden-import "json" `
        --hidden-import "datetime" `
        --hidden-import "uuid" `
        --hidden-import "typing" `
        --hidden-import "dataclasses" `
        --collect-all mediapipe `
        --collect-all cv2 `
        --exclude-module tests `
        --exclude-module pytest `
        --exclude-module unittest `
        desktop/main.py

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================================"
        Write-Host "BUILD SUCCESSFUL!"
        Write-Host "========================================================"
        Write-Host "Executable: dist\WellnessAtWork-Fixed.exe"
        Write-Host ""
        Write-Host "Test the fixed version:"
        Write-Host "  cd dist"
        Write-Host "  .\WellnessAtWork-Fixed.exe"
        Write-Host "========================================================"
    } else {
        Write-Error "Build failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Error "Build error: $($_.Exception.Message)"
} finally {
    Remove-Item -Path "app_config.json" -ErrorAction SilentlyContinue
}
