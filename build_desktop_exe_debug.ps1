<#
Build Desktop Application EXE with Debug Console for Troubleshooting

This script builds a debug version that shows console output to help identify startup issues.
#>

param (
    [string]$BackendUrl = "http://localhost:8000",
    [string]$AppName = "WellnessAtWork-Debug",
    [string]$AppVersion = "1.0.0"
)

$ErrorActionPreference = 'Stop'

Write-Host "========================================================"
Write-Host "Building WaW Desktop Application (DEBUG VERSION)"
Write-Host "========================================================"
Write-Host "Backend URL: $BackendUrl"
Write-Host "App Name: $AppName"
Write-Host "This build will show console output for debugging"
Write-Host "========================================================"

# Create app_config.json for the build with backend URL
Write-Host "==> Creating app configuration with backend URL"
$config = @{
    apiBase = $BackendUrl
    appVersion = $AppVersion
    buildTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    debug = $true
}
$configJson = $config | ConvertTo-Json -Depth 3
$configFile = "app_config.json"
Set-Content -Path $configFile -Value $configJson -Encoding UTF8
Write-Host "    Created app_config.json with backend URL: $BackendUrl"

# Generate icon if missing
Write-Host "==> Ensuring application icon exists"
if (-not (Test-Path "assets/app.ico")) {
    if (Test-Path "tools/generate_icon.py") {
        Write-Host "    Generating application icon..."
        python tools/generate_icon.py
    } else {
        Write-Warning "    Icon generator not found. Building without custom icon."
    }
}

Write-Host "==> Building DEBUG executable with console output"

try {
    # Build with console enabled for debugging
    pyinstaller --noconfirm `
        --name $AppName `
        --console `
        --onefile `
        --icon "assets/app.ico" `
        --add-data "assets;assets" `
        --add-data "app_config.json;." `
        --add-data "desktop;desktop" `
        --add-data "shared;shared" `
        --add-data "backend;backend" `
        --hidden-import "cv2" `
        --hidden-import "mediapipe" `
        --hidden-import "psutil" `
        --hidden-import "PyQt6" `
        --hidden-import "PyQt6.QtCore" `
        --hidden-import "PyQt6.QtGui" `
        --hidden-import "PyQt6.QtWidgets" `
        --hidden-import "requests" `
        --hidden-import "sqlite3" `
        --hidden-import "json" `
        --hidden-import "pathlib" `
        --hidden-import "datetime" `
        --hidden-import "uuid" `
        --hidden-import "dotenv" `
        --hidden-import "desktop.eye_tracker" `
        --hidden-import "shared.config" `
        --hidden-import "shared.api" `
        --hidden-import "shared.db" `
        --hidden-import "backend.models" `
        --collect-all mediapipe `
        --collect-all cv2 `
        --exclude-module tests `
        --exclude-module pytest `
        --exclude-module unittest `
        desktop/main.py

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================================"
        Write-Host "DEBUG BUILD SUCCESSFUL!"
        Write-Host "========================================================"
        $outputPath = "dist\$AppName.exe"
        Write-Host "Debug executable: $outputPath"
        Write-Host ""
        Write-Host "This version will show console output to help debug issues."
        Write-Host "Run it from command line to see any error messages:"
        Write-Host "  cd dist"
        Write-Host "  .\$AppName.exe"
        Write-Host ""
        Write-Host "Common startup issues to check:"
        Write-Host "  - Missing DLL files"
        Write-Host "  - Python module import errors"
        Write-Host "  - Camera/webcam access permissions"
        Write-Host "  - Backend connectivity issues"
        Write-Host "========================================================"
    } else {
        Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} catch {
    Write-Error "Build failed: $($_.Exception.Message)"
    exit 1
} finally {
    # Clean up temporary files
    Remove-Item -Path $configFile -ErrorAction SilentlyContinue
}
